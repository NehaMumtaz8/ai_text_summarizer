# =============================================================
#  chatbot_qa.py — predefined question/answer chatbot engine
#
#  Replaces the old Gemini-powered chatbot. No external AI API,
#  no API key, works completely offline/locally.
#
#  get_answer(message) -> str | None
#     Returns the matching predefined answer, or None if nothing
#     in the knowledge base matches (caller shows the fallback
#     message in that case).
#
#  SUGGESTED_QUESTIONS -> list[str]
#     The canonical question labels shown as clickable buttons in
#     the chat widget. Each one is guaranteed to match an entry
#     below, so clicking a button always gets a real answer.
# =============================================================
import re
import difflib

# ── Knowledge base ──────────────────────────────────────────
# Ordered from most specific to most general: the first entry
# whose triggers match wins, so specific topics (e.g. "pdf" +
# "how does it work") are checked before generic ones (e.g. a
# bare "pdf").
#
# Each entry: (name, [trigger phrases/keywords], answer)
QA_ENTRIES = [
    ("thanks", [
        "thank you", "thanks", "thankyou", "thank u", "appreciate it",
    ], "You're welcome! 😊 I'm always here to help you use AI Summarizer."),

    ("bye", [
        "bye", "goodbye", "good bye", "see you", "see ya", "later",
    ], "Goodbye! 👋 Have a great day, and happy learning!"),

    ("who_are_you", [
        "who are you", "tell me about yourself", "what are you",
    ], "I'm the AI Summarizer Support Assistant. I can guide you through the "
       "features of this website and answer questions about text "
       "summarization, PDFs, quizzes, flashcards, and more."),

    ("tts", [
        "text-to-speech", "text to speech", "listen to my summary",
        "listen to the summary", "tts", "can i listen",
    ], "Text-to-speech converts written text into spoken audio. This feature "
       "allows you to listen to your generated summary instead of reading it. "
       "Yes — after generating a summary, you can use the text-to-speech "
       "feature to listen to it."),

    ("quiz", [
        "quiz", "quizzes",
    ], "Quizzes help you test your understanding of the content. Questions "
       "can be generated from the processed material so you can use them "
       "for revision, which is especially useful for studying."),

    ("flashcard", [
        "flashcard", "flash card", "flashcards",
    ], "Flashcards present important information in a simple "
       "question-and-answer format. They make it easier to quickly review "
       "and remember key concepts from your study material."),

    ("what_is_bart", [
        "what is bart", "bart",
    ], "BART is a transformer-based natural language processing model "
       "developed by Facebook AI. In this project, BART Large CNN is used "
       "for AI-based text summarization."),

    ("is_ai_based", [
        "really ai-based", "really ai based", "really ai",
        "is the summarization really",
    ], "Yes. The summarization uses the BART Large CNN transformer model "
       "rather than simple keyword matching or manually written rules."),

    ("what_is_summarization", [
        "what is ai text summarization", "what is text summarization",
        "what is summarization", "what is ai summarization",
    ], "AI text summarization uses artificial intelligence to create a "
       "shorter version of a long text while keeping the most important "
       "information. It helps users understand large documents more "
       "quickly."),

    ("how_summarizer_works", [
        "how does the summarizer work", "how does summarization work",
    ], "The application analyzes the text you provide and uses the BART "
       "Large CNN model to generate a meaningful summary. The result "
       "contains the important information from the original text in a "
       "shorter form."),

    ("summarize_long", [
        "long document", "long text", "large document", "very long",
    ], "Yes. The application is designed to help reduce long text into a "
       "shorter and easier-to-read summary. Very large documents may be "
       "processed in sections depending on the model's input limitations."),

    ("pdf_how_it_works", [
        "how does pdf summarization work", "pdf summarization work",
        "how does pdf work",
    ], "When you upload a PDF, the application extracts its text using "
       "Python. The extracted text is then processed by the BART "
       "summarization model to generate a shorter summary."),

    ("pdf_upload", [
        "upload a pdf", "upload pdf", "how do i upload",
        "what file type", "which file type", "file can i upload",
    ], "Open the Dashboard and select the PDF upload option. Choose your PDF "
       "file from your computer, and the application will extract its text "
       "for summarization. The current upload feature supports PDF files."),

    ("pdf_summarize", [
        "pdf",
    ], "Go to the Dashboard and upload your PDF file using the PDF upload "
       "option. The application will extract the text from the PDF and use "
       "the BART model to generate a summary."),

    ("summarize_text", [
        "summarize my text", "summarize text", "i want to summarize",
        "how do i summarize", "how can i summarize", "can i summarize",
        "i want summary", "summarize something", "want a summary",
    ], "Sure! Go to the Dashboard and enter or paste your text into the text "
       "area. Then click the Summarize button, and the BART AI model will "
       "generate a shorter version containing the important information."),

    ("technologies", [
        "technologies", "tech stack", "what technologies", "built with",
        "what is this built with",
    ], "This project uses Python and Flask for the backend, HTML, CSS, and "
       "JavaScript for the frontend, BART Large CNN for AI summarization, "
       "and PyPDF2 for PDF text extraction. Browser Local Storage is used "
       "for user-side accounts and history."),

    ("ai_used", [
        "does this website use ai", "does the website use ai",
    ], "Yes. The main summarization feature uses the BART Large CNN AI "
       "model to generate summaries from text."),

    ("data_stored", [
        "is my data stored", "data stored", "where is my data",
    ], "The project uses browser Local Storage for user accounts and "
       "application history. It does not require MongoDB or another "
       "external database."),

    ("offline", [
        "internet connection", "need internet", "require internet",
    ], "The BART summarization model runs locally on the application's "
       "backend, so the main summarization process does not require an "
       "external AI API."),

    ("gemini_data", [
        "sent to gemini", "gemini",
    ], "No. The chatbot no longer uses Gemini or another external AI "
       "service. The predefined chatbot answers are stored within the "
       "application."),

    ("who_can_use", [
        "who can use",
    ], "Students, researchers, teachers, and anyone who needs to "
       "understand long text or documents more quickly can use this "
       "application."),

    ("create_account", [
        "create an account", "create account", "sign up", "signup",
        "register",
    ], "Click Sign Up on the website and enter the required information. "
       "Your account information is stored in your browser's Local "
       "Storage."),

    ("login", [
        "log in", "login", "how do i login",
    ], "Click Login and enter the account details you used during "
       "registration."),

    ("history", [
        "previous summaries", "find my previous", "past summaries",
        "my history",
    ], "Your previous application history is available through the "
       "history section of the Dashboard, provided it has been saved in "
       "your browser's Local Storage."),

    ("dark_mode", [
        "dark mode", "light mode", "dark/light",
    ], "Yes. The website includes a dark/light mode option that allows "
       "you to change the appearance according to your preference."),

    ("troubleshoot", [
        "doesn't work", "does not work", "not working", "something wrong",
        "isn't working", "error",
    ], "First, refresh the page and try again. Make sure your text or PDF "
       "is valid and that the Flask backend is running. If the problem "
       "continues, check the browser console and Flask terminal for error "
       "messages."),

    ("what_is_website", [
        "what is this website", "what is ai summarizer",
    ], "AI Summarizer is an AI-powered web application designed to make "
       "long documents easier to understand. It can summarize text and "
       "PDF documents and also provides learning features such as "
       "text-to-speech, quizzes, and flashcards."),

    ("how_use_website", [
        "how do i use this website", "how does this website work",
        "how to use this website", "how to use the website",
    ], "First, create an account or log in. Then open the Dashboard, "
       "enter text or upload a PDF, and use the available tools to "
       "summarize, listen to, and study the content."),

    ("can_you_help", [
        "can you help me", "help me", "help",
    ], "Of course! 😊 You can ask me about summarizing text, PDF uploads, "
       "BART, text-to-speech, quizzes, flashcards, your account, or how "
       "this website works."),

    ("what_can_you_do", [
        "what can you do",
    ], "I can help you understand and use the AI Summarizer. You can "
       "summarize text or PDF documents, listen to summaries using "
       "text-to-speech, and use features such as quizzes and flashcards."),

    ("okay", [
        "okay", "ok", "alright", "cool", "got it",
    ], "👍 Let me know if you need anything else!"),

    ("hello", [
        "hello",
    ], "Hello! 👋 Welcome to AI Summarizer. I can help you understand how "
       "this website works, summarize your text, explain the available "
       "features, and guide you through using the application."),

    ("hi", [
        "hi", "hey", "good morning", "good afternoon", "good evening",
    ], "Hi! 😊 Welcome to AI Summarizer. How can I help you today?"),
]

# ── The 11 buttons shown in the chat widget ─────────────────
# (label shown to the user, message actually sent when clicked)
SUGGESTED_QUESTIONS = [
    "👋 Hello",
    "What can you do?",
    "I want to summarize my text",
    "I want to summarize a PDF",
    "How does this website work?",
    "What is BART?",
    "What is text-to-speech?",
    "What are quizzes?",
    "What are flashcards?",
    "Is my data stored?",
    "What technologies are used?",
]

FALLBACK_ANSWER = (
    "I'm currently designed to help you with the AI Summarizer website "
    "and its features. Please choose one of the suggested questions "
    "below, and I'll be happy to help! 😊"
)


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)   # strip punctuation
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _contains(normalized_msg: str, trigger: str) -> bool:
    """Word-boundary-safe substring match, so 'hi' doesn't match inside
    'history' etc."""
    if " " in trigger:
        return trigger in normalized_msg
    return re.search(rf"\b{re.escape(trigger)}\b", normalized_msg) is not None


def get_answer(message: str) -> str:
    """Return the best matching predefined answer for a user message,
    or the friendly fallback if nothing matches closely enough."""
    if not message:
        return FALLBACK_ANSWER

    normalized = _normalize(message)
    if not normalized:
        return FALLBACK_ANSWER

    # 1) Direct keyword/phrase matching, most-specific-first (list order).
    for _name, triggers, answer in QA_ENTRIES:
        for trigger in triggers:
            if _contains(normalized, trigger):
                return answer

    # 2) Fuzzy fallback for close/simple variations that don't share an
    #    exact trigger substring (e.g. minor typos or reordered words).
    all_triggers = [t for _name, triggers, _a in QA_ENTRIES for t in triggers]
    close = difflib.get_close_matches(normalized, all_triggers, n=1, cutoff=0.72)
    if close:
        matched_trigger = close[0]
        for _name, triggers, answer in QA_ENTRIES:
            if matched_trigger in triggers:
                return answer

    # 3) Nothing matched — friendly fallback, never a raw API-style error.
    return FALLBACK_ANSWER
