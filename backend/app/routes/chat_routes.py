from flask import Blueprint, request, jsonify
from app.services.chat_service import send_message, fetch_conversation, fetch_new_messages
from app.routes.upload_routes import auth_required

bp = Blueprint("chat", __name__, url_prefix="/api/chat")

@bp.route("/send", methods=["POST"])
@auth_required
def send():
    data = request.get_json() or {}
    to_unique = data.get("to_unique_id")
    message = data.get("message")
    context_type = data.get("context_type", "global")
    context_id = data.get("context_id")
    if not message:
        return jsonify({"error": "Missing message"}), 400
    sender = request.user.get("sub")
    cm = send_message(sender_unique_id=sender, receiver_unique_id=to_unique, message=message, context_type=context_type, context_id=context_id)
    return jsonify({"message_id": cm.id, "created_at": cm.created_at}), 201

@bp.route("/history", methods=["GET"])
@auth_required
def history():
    user = request.args.get("user")
    peer = request.args.get("peer")
    if not user or not peer:
        return jsonify({"error": "Missing user or peer"}), 400
    msgs = fetch_conversation(user, peer, limit=int(request.args.get("limit", "50")))
    res = []
    for m in msgs:
        res.append({
            "id": m.id,
            "sender_unique_id": m.sender_unique_id,
            "receiver_unique_id": m.receiver_unique_id,
            "message": m.message,
            "context_type": m.context_type,
            "context_id": m.context_id,
            "created_at": m.created_at
        })
    return jsonify({"messages": res})

@bp.route("/new", methods=["GET"])
@auth_required
def new_messages():
    since = request.args.get("since")
    if not since:
        return jsonify({"error": "Missing since timestamp (ISO)"}), 400
    msgs = fetch_new_messages(since)
    res = []
    for m in msgs:
        res.append({
            "id": m.id,
            "sender_unique_id": m.sender_unique_id,
            "receiver_unique_id": m.receiver_unique_id,
            "message": m.message,
            "context_type": m.context_type,
            "context_id": m.context_id,
            "created_at": m.created_at
        })
    return jsonify({"messages": res})
