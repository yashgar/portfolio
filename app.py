from flask import (
    Flask,
    send_from_directory,
    request,
    jsonify,
    session
)

from sentence_transformers import (
    SentenceTransformer,
    util
)

import requests
import os
import re
import uuid


app = Flask(
    __name__,
    static_folder=".",
    static_url_path=""
)
os.environ["CUDA_VISIBLE_DEVICES"] = ""
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "yash-portfolio-ai-secret"
)

@app.route("/health")
def health():
    return {
        "status": "healthy"
    }, 200


class PortfolioRAGChatBot:

    def __init__(self):

        print("Loading AI portfolio assistant...")

        self.model = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )

        self.gemini_api_key = os.environ.get(
            "GEMINI_API_KEY"
        )

        self.gemini_model = os.environ.get(
            "GEMINI_MODEL",
            "gemini-2.5-flash"
        )

        self.sections = self.load_knowledge()

        self.chunks = self.create_chunks()

        self.chunk_texts = [
            chunk["text"]
            for chunk in self.chunks
        ]

        self.embeddings = self.model.encode(
            self.chunk_texts,
            convert_to_tensor=True,
            normalize_embeddings=True
        )

        self.conversations = {}

        print(
            f"Loaded {len(self.sections)} sections "
            f"and {len(self.chunks)} knowledge chunks."
        )

        if self.gemini_api_key:
            print("Gemini generation enabled.")
        else:
            print(
                "GEMINI_API_KEY not found. "
                "Local fallback enabled."
            )

        print("Portfolio AI ready.")

    # =========================================================
    # KNOWLEDGE BASE
    # =========================================================

    def load_knowledge(self):

        file_path = "knowledge.txt"

        if not os.path.exists(file_path):

            return {
                "PROFILE": [
                    (
                        "Yash Agarwal is a Computer Science "
                        "student specializing in Artificial "
                        "Intelligence and Machine Learning."
                    )
                ],
                "CONTACT": [
                    (
                        "Yash Agarwal can be contacted at "
                        "agarwalyash3004@gmail.com."
                    )
                ]
            }

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            content = file.read()

        sections = {}

        current_section = "GENERAL"

        sections[current_section] = []

        current_paragraph = []

        def save_paragraph():

            nonlocal current_paragraph

            paragraph = " ".join(
                current_paragraph
            ).strip()

            if paragraph:

                sections.setdefault(
                    current_section,
                    []
                ).append(paragraph)

            current_paragraph = []

        for raw_line in content.splitlines():

            line = raw_line.strip()

            if (
                line.startswith("[")
                and line.endswith("]")
            ):

                save_paragraph()

                current_section = (
                    line[1:-1]
                    .strip()
                    .upper()
                )

                sections.setdefault(
                    current_section,
                    []
                )

                continue

            if not line:

                save_paragraph()
                continue

            current_paragraph.append(line)

        save_paragraph()

        return {
            section: paragraphs
            for section, paragraphs
            in sections.items()
            if paragraphs
        }

    def create_chunks(self):

        chunks = []

        for section, paragraphs in (
            self.sections.items()
        ):

            for index, paragraph in enumerate(
                paragraphs
            ):

                chunks.append({
                    "section": section,
                    "paragraph_index": index,
                    "text": paragraph
                })

        return chunks

    # =========================================================
    # CONVERSATION MEMORY
    # =========================================================

    def get_history(
        self,
        conversation_id
    ):

        return self.conversations.get(
            conversation_id,
            []
        )

    def add_to_history(
        self,
        conversation_id,
        role,
        content
    ):

        if conversation_id not in (
            self.conversations
        ):

            self.conversations[
                conversation_id
            ] = []

        self.conversations[
            conversation_id
        ].append({
            "role": role,
            "content": content
        })

        self.conversations[
            conversation_id
        ] = self.conversations[
            conversation_id
        ][-8:]

    def save_history(
        self,
        conversation_id,
        user_input,
        response
    ):

        self.add_to_history(
            conversation_id,
            "user",
            user_input
        )

        self.add_to_history(
            conversation_id,
            "assistant",
            response
        )

    def history_to_text(
        self,
        conversation_id
    ):

        history = self.get_history(
            conversation_id
        )

        if not history:

            return "No previous conversation."

        lines = []

        for item in history[-6:]:

            role = (
                "Visitor"
                if item["role"] == "user"
                else "Assistant"
            )

            lines.append(
                f"{role}: {item['content']}"
            )

        return "\n".join(lines)

    # =========================================================
    # BASIC QUERY HANDLING
    # =========================================================

    def normalize_query(
        self,
        text
    ):

        text = text.lower().strip()

        text = re.sub(
            r"[^a-z0-9+#.\s]",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    def is_greeting(
        self,
        user_input
    ):

        text = self.normalize_query(
            user_input
        )

        greetings = {
            "hi",
            "hello",
            "hey",
            "hi there",
            "hello there",
            "hey there",
            "good morning",
            "good afternoon",
            "good evening"
        }

        return text in greetings

    def is_contact_question(
        self,
        user_input
    ):

        text = self.normalize_query(
            user_input
        )

        contact_phrases = [
            "contact",
            "email",
            "phone",
            "phone number",
            "reach yash",
            "contact yash",
            "connect with yash"
        ]

        return any(
            phrase in text
            for phrase in contact_phrases
        )

    # =========================================================
    # RESPONSE DEPTH
    # =========================================================

    def detect_response_mode(
        self,
        user_input
    ):

        text = self.normalize_query(
            user_input
        )

        short_phrases = [
            "brief",
            "briefly",
            "short answer",
            "quick answer",
            "one line",
            "in short"
        ]

        detailed_phrases = [
            "in detail",
            "detailed",
            "explain",
            "elaborate",
            "deep dive",
            "tell me everything"
        ]

        if any(
            phrase in text
            for phrase in short_phrases
        ):

            return "SHORT"

        if any(
            phrase in text
            for phrase in detailed_phrases
        ):

            return "DETAILED"

        return "NORMAL"

    # =========================================================
    # FOLLOW-UP DETECTION
    # =========================================================

    def is_follow_up(
        self,
        user_input
    ):

        text = self.normalize_query(
            user_input
        )

        words = set(
            re.findall(
                r"\b[a-z]+\b",
                text
            )
        )

        pronouns = {
            "it",
            "its",
            "this",
            "that",
            "he",
            "his",
            "him",
            "they",
            "their",
            "them"
        }

        follow_up_phrases = [
            "tell me more",
            "explain more",
            "more about",
            "what about",
            "how did",
            "why did",
            "what technology",
            "what technologies",
            "which technology",
            "which technologies",
            "what tools",
            "which tools",
            "what accuracy",
            "how accurate",
            "what result",
            "what was the result",
            "how does it work",
            "how did it work",
            "what did he use",
            "why is it",
            "why was it",
            "and this",
            "and that"
        ]

        phrase_match = any(
            phrase in text
            for phrase in follow_up_phrases
        )

        pronoun_match = bool(
            words.intersection(pronouns)
        )

        meaningless_follow_up = text in {
            ".",
            "..",
            "...",
            "?",
            "??"
        }

        return (
            phrase_match
            or pronoun_match
            or meaningless_follow_up
        )

    def build_search_query(
        self,
        user_input,
        conversation_id
    ):

        if not self.is_follow_up(
            user_input
        ):

            return user_input

        history = self.get_history(
            conversation_id
        )

        previous_user_messages = [
            item["content"]
            for item in history
            if item["role"] == "user"
        ]

        if not previous_user_messages:

            return user_input

        previous_question = (
            previous_user_messages[-1]
        )

        return (
            f"{previous_question}. "
            f"Follow-up question: {user_input}"
        )

    # =========================================================
    # EXACT SECTION ROUTER
    # =========================================================

    def route_sections(
        self,
        user_input
    ):

        text = self.normalize_query(
            user_input
        )

        # -----------------------------------------------------
        # EXACT PROJECT ROUTES
        # -----------------------------------------------------

        if any(
            phrase in text
            for phrase in [
                "digibanker",
                "digi banker",
                "banking chatbot"
            ]
        ):

            return [
                "PROJECT_DIGIBANKER",
                "NLP_EXPERIENCE"
            ]

        if any(
            phrase in text
            for phrase in [
                "eye on drive",
                "eyeon drive",
                "driver alert",
                "driver drowsiness",
                "drowsiness project",
                "driver distraction"
            ]
        ):

            return [
                "PROJECT_EYE_ON_DRIVE",
                "COMPUTER_VISION_EXPERIENCE"
            ]

        if any(
            phrase in text
            for phrase in [
                "phishing",
                "phishing detection",
                "phishing website",
                "url classifier",
                "url classification"
            ]
        ):

            return [
                "PROJECT_PHISHING_DETECTION",
                "IBM_INTERNSHIP",
                "CYBERSECURITY_EXPERIENCE"
            ]

        if any(
            phrase in text
            for phrase in [
                "helmet",
                "helmet detection"
            ]
        ):

            return [
                "COMPUTER_VISION_EXPERIENCE"
            ]

        # -----------------------------------------------------
        # ACHIEVEMENTS
        # -----------------------------------------------------

        if any(
            phrase in text
            for phrase in [
                "achievement",
                "achievements",
                "accomplishment",
                "accomplishments",
                "vsoc",
                "buildspace",
                "leetcode achievement"
            ]
        ):

            return [
                "ACHIEVEMENTS"
            ]

        # -----------------------------------------------------
        # EXPERIENCE
        # -----------------------------------------------------

        if any(
            phrase in text
            for phrase in [
                "ibm internship",
                "ibm experience",
                "experience at ibm",
                "worked at ibm",
                "ibm"
            ]
        ):

            return [
                "IBM_INTERNSHIP"
            ]

        if text in {
            "experience",
            "experiences",
            "work experience",
            "internship experience",
            "his experience",
            "yash experience",
            "yash experiences"
        }:

            return [
                "IBM_INTERNSHIP",
                "LEADERSHIP_AND_ACTIVITIES",
                "PROFILE"
            ]

        # -----------------------------------------------------
        # SKILLS
        # -----------------------------------------------------

        if text in {
            "skill",
            "skills",
            "technical skill",
            "technical skills",
            "his skills",
            "yash skills",
            "tech stack",
            "technologies"
        }:

            return [
                "PROGRAMMING_SKILLS",
                "TECHNICAL_SKILLS"
            ]

        if any(
            phrase in text
            for phrase in [
                "programming skill",
                "programming language",
                "languages does he know",
                "coding language"
            ]
        ):

            return [
                "PROGRAMMING_SKILLS"
            ]

        if any(
            phrase in text
            for phrase in [
                "machine learning skill",
                "ml skill",
                "machine learning experience"
            ]
        ):

            return [
                "MACHINE_LEARNING_SKILLS"
            ]

        if any(
            phrase in text
            for phrase in [
                "deep learning skill",
                "deep learning experience"
            ]
        ):

            return [
                "DEEP_LEARNING_SKILLS"
            ]

        if any(
            phrase in text
            for phrase in [
                "data science skill",
                "data science experience"
            ]
        ):

            return [
                "DATA_SCIENCE_SKILLS"
            ]

        if any(
            phrase in text
            for phrase in [
                "computer vision",
                "cv experience",
                "vision experience"
            ]
        ):

            return [
                "COMPUTER_VISION_EXPERIENCE"
            ]

        if any(
            phrase in text
            for phrase in [
                "nlp",
                "natural language processing"
            ]
        ):

            return [
                "NLP_EXPERIENCE"
            ]

        if any(
            phrase in text
            for phrase in [
                "cybersecurity",
                "cyber security"
            ]
        ):

            return [
                "CYBERSECURITY_EXPERIENCE"
            ]

        if any(
            phrase in text
            for phrase in [
                "backend",
                "backend development",
                "api experience",
                "rest api"
            ]
        ):

            return [
                "BACKEND_DEVELOPMENT"
            ]

        if any(
            phrase in text
            for phrase in [
                "database",
                "sql",
                "mongodb"
            ]
        ):

            return [
                "DATABASE_SKILLS"
            ]

        # -----------------------------------------------------
        # EDUCATION
        # -----------------------------------------------------

        if any(
            phrase in text
            for phrase in [
                "education",
                "college",
                "university",
                "upes",
                "degree",
                "graduation",
                "academic background"
            ]
        ):

            return [
                "EDUCATION"
            ]

        # -----------------------------------------------------
        # CERTIFICATIONS
        # -----------------------------------------------------

        if any(
            phrase in text
            for phrase in [
                "certification",
                "certifications",
                "certificate",
                "certificates",
                "vertex ai",
                "forage",
                "genai course",
                "responsible ai"
            ]
        ):

            return [
                "CERTIFICATIONS"
            ]

        # -----------------------------------------------------
        # PROBLEM SOLVING
        # -----------------------------------------------------

        if any(
            phrase in text
            for phrase in [
                "problem solving",
                "problem-solving",
                "technical problem",
                "coding problems",
                "leetcode"
            ]
        ):

            return [
                "PROBLEM_SOLVING",
                "ACHIEVEMENTS"
            ]

        # -----------------------------------------------------
        # STRENGTHS
        # -----------------------------------------------------

        if any(
            phrase in text
            for phrase in [
                "strength",
                "strengths",
                "strong at",
                "best qualities"
            ]
        ):

            return [
                "STRENGTHS"
            ]

        # -----------------------------------------------------
        # BEST PROJECT
        # -----------------------------------------------------

        if any(
            phrase in text
            for phrase in [
                "best project",
                "strongest project",
                "most impressive project"
            ]
        ):

            return [
                "BEST_PROJECT",
                "PROJECT_COMPARISON"
            ]

        # -----------------------------------------------------
        # PROJECT LIST
        # -----------------------------------------------------

        if text in {
            "project",
            "projects",
            "his projects",
            "yash projects",
            "tell me about projects",
            "tell me about his projects"
        }:

            return [
                "PROJECT_COMPARISON"
            ]

        # -----------------------------------------------------
        # ROLE ROUTING
        # -----------------------------------------------------

        if any(
            phrase in text
            for phrase in [
                "machine learning engineer",
                "ml engineer"
            ]
        ):

            return [
                "ML_ENGINEER_SUITABILITY",
                "BEST_PROJECT"
            ]

        if any(
            phrase in text
            for phrase in [
                "ai engineer"
            ]
        ):

            return [
                "AI_ENGINEER_SUITABILITY",
                "BEST_PROJECT"
            ]

        if any(
            phrase in text
            for phrase in [
                "data scientist",
                "data science role"
            ]
        ):

            return [
                "DATA_SCIENTIST_SUITABILITY",
                "BEST_PROJECT"
            ]

        if any(
            phrase in text
            for phrase in [
                "software engineer",
                "software developer"
            ]
        ):

            return [
                "SOFTWARE_ENGINEER_SUITABILITY"
            ]

        if any(
            phrase in text
            for phrase in [
                "best role",
                "suitable role",
                "job role",
                "career role",
                "which role",
                "role for yash"
            ]
        ):

            return [
                "BEST_ROLE_FOR_YASH"
            ]

        # -----------------------------------------------------
        # HIRING
        # -----------------------------------------------------

        if any(
            phrase in text
            for phrase in [
                "why hire",
                "hire yash",
                "good candidate",
                "suitable candidate",
                "recruiter",
                "candidate profile"
            ]
        ):

            return [
                "RECRUITER_SUMMARY",
                "STRENGTHS",
                "BEST_ROLE_FOR_YASH"
            ]

        # -----------------------------------------------------
        # PROFILE
        # -----------------------------------------------------

        if any(
            phrase in text
            for phrase in [
                "who is yash",
                "about yash",
                "tell me about yash",
                "profile",
                "introduction"
            ]
        ):

            return [
                "PROFILE"
            ]

        return []

    # =========================================================
    # RETRIEVAL
    # =========================================================

    def retrieve_from_sections(
        self,
        section_names,
        query,
        max_chunks=8
    ):

        query_embedding = self.model.encode(
            query,
            convert_to_tensor=True,
            normalize_embeddings=True
        )

        candidates = []

        for index, chunk in enumerate(
            self.chunks
        ):

            if chunk["section"] not in (
                section_names
            ):

                continue

            score = float(
                util.cos_sim(
                    query_embedding,
                    self.embeddings[index]
                )[0][0]
            )

            candidates.append({
                **chunk,
                "score": score
            })

        candidates.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        # For exact routed sections we keep enough paragraphs
        # to describe the topic properly.
        selected = candidates[:max_chunks]

        return selected

    def semantic_retrieve(
        self,
        query,
        top_k=6
    ):

        query_embedding = self.model.encode(
            query,
            convert_to_tensor=True,
            normalize_embeddings=True
        )

        scores = util.cos_sim(
            query_embedding,
            self.embeddings
        )[0]

        result_count = min(
            top_k,
            len(self.chunks)
        )

        top_results = scores.topk(
            k=result_count
        )

        results = []

        for score, index in zip(
            top_results.values,
            top_results.indices
        ):

            score_value = float(score)

            if score_value < 0.28:
                continue

            chunk = self.chunks[
                int(index)
            ]

            results.append({
                **chunk,
                "score": score_value
            })

        return results

    def retrieve_knowledge(
        self,
        user_input,
        search_query
    ):

        routed_sections = self.route_sections(
            user_input
        )

        if routed_sections:

            return self.retrieve_from_sections(
                routed_sections,
                search_query
            )

        return self.semantic_retrieve(
            search_query
        )

    # =========================================================
    # CONTEXT BUILDING
    # =========================================================

    def build_context(
        self,
        results
    ):

        if not results:

            return ""

        grouped = {}

        for result in results:

            section = result["section"]

            grouped.setdefault(
                section,
                []
            ).append(result["text"])

        blocks = []

        for section, paragraphs in (
            grouped.items()
        ):

            section_text = "\n".join(
                f"- {paragraph}"
                for paragraph in paragraphs
            )

            blocks.append(
                f"[{section}]\n{section_text}"
            )

        return "\n\n".join(blocks)

    # =========================================================
    # GEMINI PROMPT
    # =========================================================

    def build_system_instruction(
        self,
        response_mode
    ):

        length_rules = {
            "SHORT": (
                "Answer in 1 to 2 sentences."
            ),
            "NORMAL": (
                "Answer in one focused natural paragraph. "
                "Usually use 3 to 5 sentences. "
                "For a simple category question such as skills, "
                "achievements, education, or certifications, "
                "give a compact complete summary rather than "
                "an exhaustive explanation."
            ),
            "DETAILED": (
                "Give a detailed but focused answer using "
                "approximately 6 to 10 sentences when the "
                "knowledge supports that depth."
            )
        }

        return f"""
You are the AI portfolio assistant for Yash Agarwal.

Your job is to answer visitors, recruiters, and hiring managers
who ask questions about Yash.

GROUNDING RULES:

1. Use only facts in VERIFIED PORTFOLIO KNOWLEDGE.
2. Never invent skills, projects, companies, metrics, dates,
   certifications, achievements, experience, or personal details.
3. Conversation history is only for resolving genuine follow-up
   references. It is not a verified source of facts.
4. If the knowledge does not answer the question, clearly say
   that the portfolio does not provide enough verified information.
5. When information is unavailable, suggest contacting Yash at
   agarwalyash3004@gmail.com.
6. Never mention RAG, embeddings, retrieved chunks, routing,
   semantic search, context windows, or the knowledge base.

ANSWERING STYLE:

7. Answer the visitor's exact question first.
8. Sound natural, conversational, professional, and confident.
9. Talk about Yash in third person.
10. Describe Yash as an early-career or entry-level candidate.
11. Do not over-describe simple questions.
12. Do not automatically add soft skills, certifications,
    achievements, or career goals to a technical skills answer.
13. Do not automatically add technical skills to an achievements
    answer.
14. Do not automatically summarize Yash's whole profile.
15. For a named project, explain:
    - what the project is,
    - its purpose,
    - the main relevant technologies or approach,
    - and one or two important verified results when available.
16. For skills, group related technologies naturally instead of
    listing every portfolio statement.
17. For experience, prioritize actual internship or practical
    experience. Do not describe academic coursework as work
    experience.
18. For achievements, mention only verified achievements.
19. For hiring questions, connect specific project evidence and
    skills to the role.
20. Combine overlapping facts. Never repeat the same point in
    different wording.
21. Avoid repetitive openings such as:
    "Based on Yash's portfolio"
    "According to the available information"
    "Yash may be a suitable candidate"
22. Do not use phrases like "the portfolio mentions" unless
    uncertainty about a specific fact makes that necessary.
23. Do not add a contact recommendation when the question has
    already been answered successfully.
24. Do not use markdown headings for ordinary chatbot answers.
25. Never answer a different topic simply because it appeared
    in earlier conversation history.

ANSWER LENGTH:

{length_rules[response_mode]}
""".strip()

    # =========================================================
    # GEMINI GENERATION
    # =========================================================

    def call_gemini(
        self,
        user_input,
        context,
        conversation_history,
        response_mode
    ):

        if not self.gemini_api_key:

            return None

        url = (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models/"
            f"{self.gemini_model}:generateContent"
        )

        system_instruction = (
            self.build_system_instruction(
                response_mode
            )
        )

        prompt = f"""
CONVERSATION HISTORY:
{conversation_history}

VERIFIED PORTFOLIO KNOWLEDGE:
{context}

CURRENT VISITOR QUESTION:
{user_input}

Answer only the CURRENT VISITOR QUESTION.

Use the verified portfolio knowledge as the factual source.
Conversation history may only be used if the current question is
a genuine follow-up that refers to an earlier topic.

Write a natural final answer for the visitor.
""".strip()

        payload = {
            "system_instruction": {
                "parts": [
                    {
                        "text": system_instruction
                    }
                ]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.45,
                "topP": 0.90,
                "topK": 40,
                "maxOutputTokens": 450
            }
        }

        try:

            response = requests.post(
                url,
                params={
                    "key": self.gemini_api_key
                },
                json=payload,
                timeout=30
            )

            response.raise_for_status()

            data = response.json()

            candidates = data.get(
                "candidates",
                []
            )

            if not candidates:

                return None

            parts = (
                candidates[0]
                .get("content", {})
                .get("parts", [])
            )

            generated_text = " ".join(
                part.get("text", "")
                for part in parts
                if part.get("text")
            ).strip()

            if not generated_text:

                return None

            return generated_text

        except requests.RequestException as error:

            print(
                "Gemini API request failed:",
                error
            )

            return None

        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError
        ) as error:

            print(
                "Gemini response parsing failed:",
                error
            )

            return None

    # =========================================================
    # LOCAL FALLBACK
    # =========================================================

    def local_fallback_response(
        self,
        results,
        response_mode
    ):

        if not results:

            return self.unknown_response()

        limits = {
            "SHORT": 2,
            "NORMAL": 4,
            "DETAILED": 8
        }

        sentence_limit = limits[
            response_mode
        ]

        selected_sentences = []

        seen = set()

        for result in results:

            sentences = re.split(
                r"(?<=[.!?])\s+",
                result["text"]
            )

            for sentence in sentences:

                sentence = sentence.strip()

                if not sentence:
                    continue

                normalized = re.sub(
                    r"[^a-z0-9]+",
                    " ",
                    sentence.lower()
                ).strip()

                if normalized in seen:
                    continue

                seen.add(normalized)

                selected_sentences.append(
                    sentence
                )

                if (
                    len(selected_sentences)
                    >= sentence_limit
                ):

                    return " ".join(
                        selected_sentences
                    )

        if selected_sentences:

            return " ".join(
                selected_sentences
            )

        return self.unknown_response()

    # =========================================================
    # FIXED RESPONSES
    # =========================================================

    def greeting_response(self):

        return (
            "Hi! I'm Yash's AI assistant. "
            "You can ask me about his projects, "
            "technical skills, IBM experience, "
            "education, achievements, certifications, "
            "or the roles that fit his profile."
        )

    def contact_response(self):

        return (
            "You can reach Yash at "
            "agarwalyash3004@gmail.com. "
            "His LinkedIn, GitHub, and LeetCode "
            "profiles are also linked on this portfolio."
        )

    def unknown_response(self):

        return (
            "Yash's portfolio does not provide enough "
            "verified information for me to answer that "
            "accurately. You can contact him at "
            "agarwalyash3004@gmail.com for more details."
        )

    # =========================================================
    # MAIN RESPONSE PIPELINE
    # =========================================================

    def get_response(
        self,
        user_input,
        conversation_id
    ):

        user_input = user_input.strip()

        if not user_input:

            return "Please ask me a question."

        if self.is_greeting(
            user_input
        ):

            response = (
                self.greeting_response()
            )

            self.save_history(
                conversation_id,
                user_input,
                response
            )

            return response

        if self.is_contact_question(
            user_input
        ):

            response = (
                self.contact_response()
            )

            self.save_history(
                conversation_id,
                user_input,
                response
            )

            return response

        response_mode = (
            self.detect_response_mode(
                user_input
            )
        )

        search_query = (
            self.build_search_query(
                user_input,
                conversation_id
            )
        )

        results = (
            self.retrieve_knowledge(
                user_input,
                search_query
            )
        )

        context = self.build_context(
            results
        )

        conversation_history = (
            self.history_to_text(
                conversation_id
            )
        )

        response = self.call_gemini(
            user_input=user_input,
            context=context,
            conversation_history=(
                conversation_history
            ),
            response_mode=response_mode
        )

        if not response:

            response = (
                self.local_fallback_response(
                    results,
                    response_mode
                )
            )

        self.save_history(
            conversation_id,
            user_input,
            response
        )

        return response


chatbot = PortfolioRAGChatBot()


# =============================================================
# FLASK ROUTES
# =============================================================


@app.route("/")
def serve_index():

    return send_from_directory(
        ".",
        "index.html"
    )


@app.route(
    "/chat",
    methods=["POST"]
)
def chat():

    try:

        data = (
            request.get_json(
                silent=True
            )
            or {}
        )

        user_message = data.get(
            "message",
            ""
        ).strip()

        if not user_message:

            return jsonify({
                "response": (
                    "Please say something!"
                )
            })

        if "conversation_id" not in session:

            session[
                "conversation_id"
            ] = str(
                uuid.uuid4()
            )

        conversation_id = session[
            "conversation_id"
        ]

        response = chatbot.get_response(
            user_message,
            conversation_id
        )

        return jsonify({
            "response": response
        })

    except Exception as error:

        print(
            f"Chat error: {error}"
        )

        return jsonify({
            "response": (
                "Sorry, I encountered an error "
                "while processing your question."
            )
        }), 500


@app.route(
    "/reset-chat",
    methods=["POST"]
)
def reset_chat():

    conversation_id = session.get(
        "conversation_id"
    )

    if conversation_id:

        chatbot.conversations.pop(
            conversation_id,
            None
        )

    session[
        "conversation_id"
    ] = str(
        uuid.uuid4()
    )

    return jsonify({
        "success": True
    })


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=7860,
        debug=False
    )
