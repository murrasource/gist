-- **SETUP**
--
-- `/etc/dovecot/conf.d/10-mail.conf`
--      mail_plugins = quota mail_lua notify push_notification push_notification_lua
--
-- `/etc/dovecot/conf.d/90-gist.conf`
--      plugin {
--          push_notification_driver = lua:file=/gist/push.lua
--          push_lua_url = https://gist.email/processor/new-message
--      }
--
-- `/gist/push.lua`
--      THIS FILE
--
-- $ apt install lua5.3
-- $ LUA_PATH=/gist
-- $ apt -y install libssl-dev
-- $ wget https://raw.githubusercontent.com/rxi/json.lua/master/json.lua -O /gist/json.lua
-- $ luarocks install luasocket
-- $ luarocks install luasec
--
-- **DESCRIPTION**
-- Whenever a new mesasge is received by Dovecot, the endpoint specified by $push_lua_url
-- is sent a POST message to given JSON data about the message.
-- 

local https = require "ssl.https"
local ltn12 = require "ltn12"
local json = require "json"


function table_get(t, k, d)
  return t[k] or d
end

function dovecot_lua_notify_begin_txn(user)
    return {user=user, event=dovecot.event(), endpoint=user:plugin_getenv("push_lua_url"), states={}, messages={}}
end

function dovecot_lua_notify_event_message_new(context, event)
    local maildir = context.user:mailbox(event.mailbox)
    maildir:sync()
    local status = maildir:status(dovecot.storage.STATUS_RECENT, dovecot.storage.STATUS_UNSEEN, dovecot.storage.STATUS_MESSAGES)
    maildir:free()
    table.insert(context.messages, {
        user = context.user.username,
        to = event.to_address,
        uidvalidity = event.uid_validity,
        uid = event.uid,
        folder = event.mailbox,
        event = event.name,
        from = event.from_address,
    })
end

function dovecot_lua_notify_end_txn(context)
    for i,msg in ipairs(context.messages) do
        local event = dovecot.event(context.event)
        event:set_name("lua_notify_mail_finished")
        reqbody = json.encode(msg)
        event:log_info(context.endpoint .. " - sending " .. reqbody)
        local _, status, headers, statusline = https.request {
            method = "POST",
            url = context.endpoint,
            headers={
                ["content-type"] = "application/json; charset=utf-8",
                ["content-length"] = tostring(#reqbody)
            },
            source = ltn12.source.string(reqbody)
        }
        event:add_int("result_code", status)
        event:log_info("Mail notify status " .. tostring(status))
    end
end