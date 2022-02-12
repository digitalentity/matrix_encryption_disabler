### E2EE disabling plugin for Synapse

This [Pluggable Module](https://matrix-org.github.io/synapse/latest/modules/index.html) disables end-to-end encryption in a self-hosted Synapse servers. It works by stripping out requests for encryption from newly created rooms, patching power levels to prevent users from enabling encryption and additionally filtering out events for enabling E2EE on already existing rooms if a user or a room belongs to a configured list of servers.

This logic will work also on federated servers as long as they verify and enforce power levels.

Possible use-cases:
 * A legal requirement to provide auditable chat logs
 * Simplify deployments and operation for private homeservers where users don't care about E2EE and want to avoid issues with device verification, server-backed-up-keys etc.

Once this feature is implemented on Synapse side (https://github.com/matrix-org/synapse/issues/4401) this plugin will become obsolete.

### Example config:

Plugin will strip away encryption from newly created rooms.
In addition the plugin will filter out events for enabling encryption on room based on the server:
  - deny_encryption_for_users_of: if the event sender is on the server in the list (i.e. @user:example.org)
  - deny_encryption_for_rooms_of: if the room is on the server in the list (i.e. !room:example.org)

In your `homeserver.yaml`:

```
modules:
 - module: "matrix_e2ee_filter.EncryptedRoomFilter"
   config:
     deny_encryption_for_users_of: ['example.org']
     deny_encryption_for_rooms_of: ['example.org']
```

You may also want to add the following to your logging config to debug the plugin:

```
loggers:
    matrix_e2ee_filter:
        level: INFO
```

### Caveats

This is not bullet-proof, a federated server that doesn't respect power levels may still allow users to enable encryption which will allow 3p users on other servers belonging to federation to freely use e2ee. This will create a divergence in room state and users on the server where this plugin is enabled won't be able to read encrypted messages - from their point of view the room will still be unencrypted.
