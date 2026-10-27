
# Socket.IO Guide

## Connection

JWT Authentication required before joining rooms.

## Rooms

group_<id>
dm_<id>

## Events

connect
disconnect
join_group
leave_group
send_group_message
edit_group_message
delete_group_message
typing
notification
read_receipt
delivery_status

## Redis

Redis adapter for horizontal scaling.

## Best Practices

- Authorize every event.
- Validate payloads.
- Prevent spam.
- Handle reconnects.
- Queue offline notifications.
