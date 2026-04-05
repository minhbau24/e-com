import { useMemo, useRef, useState } from "react";
import { sendChatMessage } from "../api/chat";

function ChatWidget({ currentUser }) {
    const [isOpen, setIsOpen] = useState(false);
    const [input, setInput] = useState("");
    const [isSending, setIsSending] = useState(false);
    const [messages, setMessages] = useState([
        {
            id: "welcome",
            role: "assistant",
            text: "Xin chao. Minh la tro ly mua sam. Ban muon tim san pham nao?",
        },
    ]);
    const viewportRef = useRef(null);

    const userId = useMemo(() => String(currentUser?.id || "guest"), [currentUser?.id]);

    const scrollToBottom = () => {
        if (viewportRef.current) {
            viewportRef.current.scrollTop = viewportRef.current.scrollHeight;
        }
    };

    const pushMessage = (role, text) => {
        setMessages((prev) => [
            ...prev,
            {
                id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                role,
                text,
            },
        ]);
        window.setTimeout(scrollToBottom, 0);
    };

    const submitMessage = async () => {
        const query = input.trim();
        if (!query || isSending) {
            return;
        }

        pushMessage("user", query);
        setInput("");

        try {
            setIsSending(true);
            const data = await sendChatMessage({ user_id: userId, query, debug: true });
            const answer = String(data?.response || data?.detail || "Xin loi, hien tai toi chua tra loi duoc.").trim();
            pushMessage("assistant", answer);
        } catch (error) {
            const detail =
                error?.response?.data?.detail ||
                error?.message ||
                "Khong the ket noi chatbot luc nay. Vui long thu lai.";
            pushMessage("assistant", String(detail));
        } finally {
            setIsSending(false);
        }
    };

    return (
        <>
            <button
                type="button"
                className="chat-fab btn"
                onClick={() => setIsOpen((prev) => !prev)}
                aria-label={isOpen ? "Close chat" : "Open chat"}
                title={isOpen ? "Close chat" : "Open chat"}
            >
                {isOpen ? "-" : "..."}
            </button>

            <section className={`chat-panel card border-0 shadow-lg ${isOpen ? "open" : ""}`} aria-hidden={!isOpen}>
                <header className="chat-panel-head d-flex align-items-center justify-content-between">
                    <div>
                        <strong>Assistant</strong>
                        <div className="small text-muted">E-com chat API</div>
                    </div>
                    <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => setIsOpen(false)}>
                        Close
                    </button>
                </header>

                <div className="chat-panel-body" ref={viewportRef}>
                    {messages.map((msg) => (
                        <div key={msg.id} className={`chat-bubble ${msg.role === "user" ? "chat-bubble-user" : "chat-bubble-assistant"}`}>
                            {msg.text}
                        </div>
                    ))}
                    {isSending ? <div className="chat-bubble chat-bubble-assistant">Dang tra loi...</div> : null}
                </div>

                <footer className="chat-panel-foot d-flex gap-2">
                    <input
                        type="text"
                        className="form-control"
                        placeholder="Nhap cau hoi cua ban..."
                        value={input}
                        onChange={(event) => setInput(event.target.value)}
                        onKeyDown={(event) => {
                            if (event.key === "Enter") {
                                event.preventDefault();
                                submitMessage();
                            }
                        }}
                        disabled={isSending}
                    />
                    <button type="button" className="btn btn-danger" onClick={submitMessage} disabled={isSending || !input.trim()}>
                        Send
                    </button>
                </footer>
            </section>
        </>
    );
}

export default ChatWidget;
