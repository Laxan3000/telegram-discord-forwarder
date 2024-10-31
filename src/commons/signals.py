import asyncio
from gvars import PENDING_TIMEOUT, PENDING_CHECKS_INTERVAL


async def wait_association_acceptance(uuid: str) -> bool:
    """
    Wait for the association with the same UUID to complete.
    Returns False if the association was not completed.
    """
    from ..commons.database import database
    
    for _ in range((PENDING_TIMEOUT / PENDING_CHECKS_INTERVAL).__floor__()):
        await asyncio.sleep(PENDING_CHECKS_INTERVAL)
        if not database.is_association_pending(uuid):
            return True
    else:
        from time import time
        
        database.delete_selected_pending_associations(unix=int(time()))
        return False
