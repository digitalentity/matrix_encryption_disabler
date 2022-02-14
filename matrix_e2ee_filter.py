import logging
import synapse
from typing import Optional, Tuple, Union
from synapse import module_api

logger = logging.getLogger(__name__)

# Example config:
#   Plugin will strip away encryption from newly created rooms.
#
# If `patch_power_levels` option is set to `True` the plugin will additionally patch the `m.room.power_levels` event 
# and set the required power level for enabling encryption to 150 which is higher than the room creator level (100), 
# effectively preventing anybody from enabling the encryption. Note that this may be incompatible with other servers.
#
#   In addition the plugin will filter out events for enabling encryption on room based on the server:
#     - deny_encryption_for_users_of: if the event sender is on the server in the list (i.e. @user:example.org)
#     - deny_encryption_for_rooms_of: if the room is on the server in the list (i.e. !room:example.org)

# modules:
#   - module: "matrix_e2ee_filter.EncryptedRoomFilter"
#     config:
#       deny_encryption_for_users_of: ['example.org']
#       deny_encryption_for_rooms_of: ['example.org']
#       patch_power_levels: False

# You may also want to add the following to your logging config to debug the plugin:

# loggers:
#     matrix_e2ee_filter:
#         level: INFO

def _patch_room_power_levels(room_power_levels, requester_user_id):
    DEFAULT_EVENT_ACL = {
        'm.room.name': 50,
        'm.room.power_levels': 100,
        'm.room.history_visibility': 100,
        'm.room.canonical_alias': 50,
        'm.room.avatar': 50,
        'm.room.tombstone': 100,
        'm.room.server_acl': 100,
        'm.room.encryption': 100
    }
    # Generate the new event if it's None or doesn't seem valid
    if not room_power_levels or 'content' not in room_power_levels:
        room_power_levels = {
            'type': 'm.room.power_levels',
            'sender': requester_user_id,
            'content': {
                'users': { requester_user_id: 100 },
                'users_default': 0,
                'events': DEFAULT_EVENT_ACL,
                'events_default': 0,
                'state_default': 50,
                'ban': 50,
                'kick': 50,
                'redact': 50,
                'invite': 0,
                'historical': 100
            }
        }

    content = room_power_levels['content']

    # Figure out max user power level
    if 'users' not in content:
        content['users'] = { requester_user_id: 100 }
        enc_power_level = 150
    else:
        enc_power_level = max(content['users'].values()) + 50

    # Patch 'events' field if present, if not - use default and still patch
    if 'events' not in content:
        content['events'] = DEFAULT_EVENT_ACL

    content['events']['m.room.encryption'] = enc_power_level

    return room_power_levels


class EncryptedRoomFilter:

    def __init__(self, config: dict, api: module_api):
        self.api = api
        self.deny_user_servers = config.get("deny_encryption_for_users_of", [])
        self.deny_room_servers = config.get("deny_encryption_for_rooms_of", [])
        self.patch_power_levels = config.get("patch_power_levels", False)
        self.api.register_third_party_rules_callbacks(on_create_room = self.on_create_room,)
        self.api.register_spam_checker_callbacks(check_event_for_spam=self.check_event_for_spam,)
        logger.info('Registered custom rule filter: EncryptedRoomFilter')
        logger.info('Deny lists: users of %s; rooms of %s', self.deny_user_servers, self.deny_room_servers)


    async def check_event_for_spam(self, event: "synapse.events.EventBase") -> Union[bool, str]:
        # This is probably unnecessary if m.room.power_levels are set correctly
        # Let's keep it just in case
        event_dict = event.get_dict()
        try:
            event_type = event_dict.get('type', None)
            if event_type == 'm.room.encryption':
                _, user_server = event_dict['sender'].split(':', 2)
                _, room_server = event_dict['room_id'].split(':', 2)

                if user_server in self.deny_user_servers:
                    logger.warn('Denied E2EE for %s / requestor', event_dict.get('room_id', '<unknown>'))
                    return 'Encryption is not allowed'
                elif room_server in self.deny_room_servers:
                    logger.warn('Denied E2EE for %s / room server', event_dict.get('room_id', '<unknown>'))
                    return 'Encryption is not allowed'
        except Exception:
            logger.warn('Exception when trying to handle the event: %s', event_dict)
            return 'Denied because an error occurred when processing the request'
        return False


    async def on_create_room(self, requester: "synapse.types.Requester", request_content: dict, is_requester_admin: bool,) -> None:
        # Cut out encryption setting for the room, force room to be unencrypted
        # Note that this still doesn't block users from enabling encryption at a later stage

        filtered_initial_state = []
        initial_power_levels = None
        for event in request_content.get('initial_state', []):
            if event['type'] in ['m.room.encryption', 'm.room.power_levels']:
                logger.info('Stripped "%s" from %s', event['type'], request_content.get('name', ''))

                # If initial power levels event is present - store it for future use
                if event['type'] == 'm.room.power_levels':
                    initial_power_levels = event
            else:
                filtered_initial_state.append(event)

        # Build the miinimalistic power m.room.power_levels:
        #
        # Handler `on_create_room` is called early in the room creation flow, before inviting users: 
        # https://github.com/matrix-org/synapse/blob/develop/synapse/handlers/room.py#L686-L690
        #
        # Power levels are populated/generated later in the room creation flow. To make sure initial state is correct
        # we need to mimic the server defaults. Defaults takes from here:
        # https://github.com/matrix-org/synapse/blob/develop/synapse/handlers/room.py#L1015-L1035
        if self.patch_power_levels:
            initial_power_levels = _patch_room_power_levels(initial_power_levels, requester.user.to_string())

        # Inject back the power level structure
        if initial_power_levels:
            filtered_initial_state.append(initial_power_levels)

        request_content['initial_state'] = filtered_initial_state
