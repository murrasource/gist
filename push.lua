-- To use:
--
-- plugin {
--   push_notification_driver = lua:file=/gist/push.lua
--   push_lua_url = https://gist.email/processor/new-message
-- }
--
-- server is sent a POST message to given url with parameters
--

local client = nil
local url = require "socket.url"

function table_get(t, k, d)
  return t[k] or d
end

function script_init()
  client = dovecot.http.client({debug=True, timeout=10000})
  return 0
end

function dovecot_lua_notify_begin_txn(user)
  return {user=user, event=dovecot.event(), ep=user:plugin_getenv("push_lua_url"), states={}, messages={}}
end

function dovecot_lua_notify_event_message_new(ctx, event)
  -- get mailbox status
  local mbox = ctx.user:mailbox(event.mailbox)
  mbox:sync()
  local status = mbox:status(dovecot.storage.STATUS_RECENT, dovecot.storage.STATUS_UNSEEN, dovecot.storage.STATUS_MESSAGES)
  mbox:free()
  ctx.states[event.mailbox] = status
  table.insert(ctx.messages, {from=event.from,subject=event.subject,mailbox=event.mailbox})
end

function dovecot_lua_notify_event_message_append(ctx, event, user)
  dovecot_lua_notify_event_message_new(ctx, event, user)
end

function dovecot_lua_notify_end_txn(ctx)
  -- report all states
  for i,msg in ipairs(ctx.messages) do
    local e = dovecot.event(ctx.event)
    e:set_name("lua_notify_mail_finished")
    reqbody = "mailbox=" .. url.escape(msg.mailbox) .. "&from=" .. url.escape(table_get(msg, "from", "")) .. "&subject=" .. url.escape(table_get(msg, "subject", ""))
    e:log_debug(ctx.ep .. " - sending " .. reqbody)
    local rq = client:request({url=ctx["ep"], method="POST"})
    rq:set_payload(reqbody)
    rq:add_header("content-type", "application/x-www-form-url.escaped")
    local code = rq:submit():status()
    e:add_int("result_code", code)
    e:log_info("Mail notify status " .. tostring(code))
  end

  for box,state in pairs(ctx.states) do
    local e = dovecot.event()
    e:set_name("lua_notify_mailbox_finished")
    reqbody = "mailbox=" .. url.escape(state.mailbox) .. "&recent=" .. tostring(state.recent) .. "&unseen=" .. tostring(state.unseen) .. "&messages=" .. tostring(state.messages)
    e:log_debug(ctx.ep .. " - sending " .. reqbody)
    local rq = client:request({url=ctx["ep"], method="POST"})
    rq:set_payload(reqbody)
    rq:add_header("content-type", "application/x-www-form-url.escaped")
    local code = rq:submit():status()
    e:add_int("result_code", code)
    e:log_info("Mailbox notify status " .. tostring(code))
  end

end