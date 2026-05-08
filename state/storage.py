import json
import logging
import asyncio
from typing import Dict, Optional

from config import STATE_FILE  # Keep for migration, but not used
from state.models import BotState
from db.database import save_user_state, load_user_state, load_all_user_states, clear_user_states

STATE_LOCK = asyncio.Lock()

logger = logging.getLogger(__name__)

# In-memory cache for active user states (memory optimization)
USER_STATES_CACHE: Dict[int, BotState] = {}
CACHE_SIZE = 100  # Limit cache to prevent memory bloat

# ---------------------------------------------------
# Cache Management (Memory Optimization)
# ---------------------------------------------------

def _get_cache_key(user_id: int) -> int:
    return user_id

def _is_cache_full() -> bool:
    return len(USER_STATES_CACHE) >= CACHE_SIZE

def _evict_oldest():
    """Simple LRU eviction - remove oldest accessed"""
    if USER_STATES_CACHE:
        oldest_user = next(iter(USER_STATES_CACHE))
        del USER_STATES_CACHE[oldest_user]
        logger.debug(f"Evicted user state from cache: {oldest_user}")

def _load_from_cache(user_id: int) -> Optional[BotState]:
    return USER_STATES_CACHE.get(user_id)

def _save_to_cache(user_id: int, state: BotState):
    if _is_cache_full():
        _evict_oldest()
    USER_STATES_CACHE[user_id] = state

def _remove_from_cache(user_id: int):
    USER_STATES_CACHE.pop(user_id, None)

# ---------------------------------------------------
# Load/Save User States (Database-Backed)
# ---------------------------------------------------

def load_bot_state():
    """Load all user states from DB into cache (for migration/initial load)"""
    try:
        all_states = load_all_user_states()
        for user_id_str, state_json in all_states.items():
            user_id = int(user_id_str)
            state_dict = json.loads(state_json)
            state = BotState.from_dict(state_dict)
            _save_to_cache(user_id, state)
        logger.info("Loaded %d user states from database", len(all_states))
    except Exception:
        logger.exception("Failed to load states from database")
        USER_STATES_CACHE.clear()

def get_user_state(user_id: int) -> BotState:
    """Get user state, loading from DB if not in cache"""
    state = _load_from_cache(user_id)
    if state is None:
        # Load from DB
        state_json = load_user_state(user_id)
        if state_json:
            try:
                state_dict = json.loads(state_json)
                state = BotState.from_dict(state_dict)
            except Exception:
                logger.exception(f"Failed to deserialize state for user {user_id}")
                state = BotState()
        else:
            state = BotState()
        _save_to_cache(user_id, state)
    return state

async def update_user_state(user_id: int, state: BotState):
    """Update user state in cache and DB"""
    async with STATE_LOCK:
        _save_to_cache(user_id, state)
        state_json = json.dumps(state.to_dict(), ensure_ascii=False)
        await asyncio.to_thread(save_user_state, user_id, state_json)

def persist_all():
    """Persist all cached states to DB"""
    for user_id, state in USER_STATES_CACHE.items():
        try:
            state_json = json.dumps(state.to_dict(), ensure_ascii=False)
            save_user_state(user_id, state_json)
        except Exception:
            logger.exception(f"Failed to persist state for user {user_id}")
    logger.info("Persisted %d user states to database", len(USER_STATES_CACHE))

async def start_periodic_save():
    """Start periodic save task (now saves cache to DB)"""
    global _save_task
    if _save_task is None or _save_task.done():
        _save_task = asyncio.create_task(_periodic_save())
        logger.info("Periodic state saving started")

async def stop_periodic_save():
    """Stop periodic save and persist final state"""
    global _save_task
    if _save_task and not _save_task.done():
        _save_task.cancel()
        try:
            await _save_task
        except asyncio.CancelledError:
            pass
    # Final persist
    await asyncio.to_thread(persist_all)
    logger.info("Periodic state saving stopped")

# ---------------------------------------------------
# Periodic Save
# ---------------------------------------------------
SAVE_INTERVAL = 300  # Save every 5 minutes
_save_task = None

async def _periodic_save():
    """Periodically save cached states to DB"""
    while True:
        await asyncio.sleep(SAVE_INTERVAL)
        try:
            async with STATE_LOCK:
                await asyncio.to_thread(persist_all)
            logger.debug("Periodic state save completed")
        except Exception:
            logger.exception("Periodic state save failed")
