import logging
import synapse
from typing import Optional, Tuple
from synapse import module_api

logger = logging.getLogger(__name__)

# Example config:
#   Plugin will strip away encryption from newly created rooms.
#   In addition the plugin will filter out events for enabling encryption on room based on the server:
#     - deny_encryption_for_users_of: if the event sender is on the server in the list (i.e. @user:example.org)
#     - deny_encryption_for_rooms_of: if the room is on the server in the list (i.e. #room:example.org)
#
# third_party_event_rules:
#   module: "matrix_e2ee_filter.EncryptedRoomFilter"
#   config:
#     deny_encryption_for_users_of: ['example.org']
#     deny_encryption_for_rooms_of: ['example.org']
#
# You may also want to add the following to your logging config to debug the plugin:
#
# loggers:
#     matrix_e2ee_filter:
#         level: INFO
#

class EncryptedRoomFilter:

    def __init__(self, config: dict, module_api: module_api):
        self.api = module_api
        self.deny_user_servers = config.get("deny_encryption_for_users_of", [])
        self.deny_room_servers = config.get("deny_encryption_for_rooms_of", [])
        self.api.register_third_party_rules_callbacks(on_create_room = self.on_create_room,)
        self.api.register_third_party_rules_callbacks(check_event_allowed = self.check_event_allowed,)
        logger.info('Registered custom rule filter: EncryptedRoomFilter')
        logger.info('Deny lists: users of %s; rooms of %s', self.deny_user_servers, self.deny_room_servers)


    async def check_event_allowed(self, event: "synapse.events.EventBase", state_events: "synapse.types.StateMap",) -> Tuple[bool, Optional[dict]]:
        event_dict = event.get_dict()
        try:
            event_type = event_dict.get('type', None)
            if event_type == 'm.room.encryption':
                _, user_server = event_dict['sender'].split(':', 2)
                _, room_server = event_dict['room_id'].split(':', 2)

                if user_server in self.deny_user_servers:
                    logger.warn('Denied encryption for %s because of requestor', event_dict.get('room_id', '<unknown>'))
                    return (False, event_dict)
                elif room_server in self.deny_room_servers:
                    logger.warn('Denied encryption for %s because of room server', event_dict.get('room_id', '<unknown>'))
                    return (False, event_dict)
        except Exception:
            raise
            return (False, event_dict)
        return (True, event_dict)


    async def on_create_room(self, requester: "synapse.types.Requester", request_content: dict, is_requester_admin: bool,) -> None:
        # Cut out encryption setting for the room, force room to be unencrypted
        # Note that this still doesn't block users from enabling encryption at a later stage
        log.info('%s', requester.get_dict())
        filtered_initial_state = []
        for event in request_content.get('initial_state', []):
            if event['type'] not in ['m.room.encryption']:
                filtered_initial_state.append(event)
            else:
                logger.info('Stripped away encryption request from %s', request_content.get('name', ''))
        request_content['initial_state'] = filtered_initial_state
