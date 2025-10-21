import json, time, requests, logging
from typing import List
from ...domain import config

logger = logging.getLogger(__name__)

_session = requests.Session()
_adapter = requests.adapters.HTTPAdapter(pool_connections=16, pool_maxsize=16)
_session.mount("http://", _adapter); _session.mount("https://", _adapter)

def _generate_gemini_prompt(breed: str, colors: str, features: str) -> str:
    """LlmService.java의 GeminiPrompt.generatePrompt() 로직을 Python으로 구현"""
    return f"""
            You are an expert data normalizer for a dog image-matching service.
            Your sole purpose is to generate standardized, short English sentences for CLIP text encoding based on user input.
            You must follow all rules with extreme precision to ensure the output is deterministic, detailed, and structurally perfect.
            
            **Task:**
            Produce exactly 3 short English sentences describing the same dog.
            
            **Output Format:**
            Return ONLY a JSON object with keys "sentence1", "sentence2", and "sentence3".
            Example: {{"sentence1": "First sentence.", "sentence2": "Second sentence.", "sentence3": "Third sentence."}}
            
            ---
            **GLOBAL RULES:**
            1.  **Sentence Count:** Exactly 3 sentences.
            2.  **Word Count:** Each sentence must be 25 words or less.
            3.  **Content:** Use plain ASCII characters only. No emojis.
            4.  **Certainty:** Do not use words of uncertainty (e.g., maybe, probably, seems like). State confirmed facts only.
            5.  **Negation:** Use "no" or "without" to express absence (e.g., "without collar").
            6.  **Degerminism:** Always generate the same output for identical input. No randomness.
            
            ---
            **SENTENCE STRUCTURE RULES:**
            
            **Sentence 1 (Main Description & High-Level Summary):**
            -   This sentence serves as a general summary. It MUST include breed, colors, accessories (with color), and temperament if available.
            -   It should ALSO include general physical descriptions (e.g., "long body", "fluffy tail") if provided.
            -   **CRITICAL:** This sentence MUST NOT list the specific, detailed items that will be described in Sentence 2 (i.e., do not repeat "Special marks" or "Accessories/appearance" items).
            
            **Sentence 2 (Distinctive Features):**
            -   This sentence has conditional logic based on the input.
            -   **IF** the text contains distinctive visual identifiers, the sentence MUST start with "Special marks: " followed by 2-4 concise noun phrases.
                -   **Definition:** "Special marks" includes BOTH color patterns (e.g., "white socks", "heart-shaped patch") AND unique physical traits (e.g., "unusually large right ear", "folded ear tip").
                -   Example: "Special marks: white blaze on face, folded left ear tip."
            -   **ELSE IF** no markings are provided but accessories or other appearance notes are, the sentence MUST start with "Accessories/appearance: " followed by a list of items.
                -   This includes listed accessories AND general appearance notes like grooming (e.g., "round haircut").
                -   Example: "Accessories/appearance: red harness, round haircut."
            -   **ELSE** (if no markings AND no accessories/appearance notes), use this fallback format: "Appearance summary: [Breed] with [color] coat."
                -   Example: "Appearance summary: Shiba Inu with tan and white coat."
            
            **Sentence 3 (Simple Summary):**
            -   Provide a very short, structured summary.
            -   Format: "[Breed]; colors: [color1], [color2]."
            
            ---
            **CONTENT CONSTRAINT RULES:**
            
            **Color Rules:**
            -   You MUST only use colors from this whitelist: {{black, white, brown, tan, cream, gray, brindle, sable, fawn}}.
            -   Normalize user-provided colors to the closest color in the whitelist (e.g., "light brown" -> "tan", "chocolate" -> "brown").
            -   Use a maximum of 3 colors.
            -   Additionally, if user input includes accessory or non-fur colors, you may also use extended colors from this list: {{e.g., "red", "blue", "green", "yellow", "orange", "pink", "purple", "gold", "silver", "beige"}}. These are mainly allowed for accessories (e.g., "blue collar", "pink bow").
            -   Always prefer coat colors from the primary list for fur and body description, and use extended colors only for accessories or explicitly mentioned special marks.
            
            **Accessory & Detail Rules:**
            -   **CRITICAL:** When an accessory is mentioned, you MUST preserve its details. If a color is provided for an accessory, you MUST include it ANY color information exists in user input OR color list.(e.g., render "green collar", not just "collar").
            -   If the user did not specify an accessory color, you MUST explicitly write "uncolored [accessory]" instead of omitting the color.
            			Example:
            				- Input: “wearing a bow” → Output: “wearing an uncolored bow.”
            				- Input: “wearing a red collar” → Output: “wearing a red collar.”
            -   List specific items (e.g., "sweater", "shoes"). Do not over-generalize to "clothes" if specifics are given.
            -   Recognized accessory types include: {{collar, harness, bow, scarf, clothes, muzzle, shoes}}.
            
            **Temperament Rules:**
            -   If a temperament is mentioned, you may use it. Consider normalizing to this set if possible: {{timid, friendly, energetic, aggressive, playful}}. Omit if not provided.
            
            ---
            **USER INPUT:**
            
            **Breed:**
            {breed}
            
            **Colors:**
            {colors}
            
            **Free Text Description:**
            {features}
            """

def _call_gemini_api(prompt: str) -> dict:
    """Gemini API 직접 호출 (LlmService.java 로직 참고)"""
    if not config.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다. 환경변수나 config.py에서 API 키를 설정해주세요.")
    
    # API 전체 URL 조합
    full_url = f"{config.GEMINI_API_URL}?key={config.GEMINI_API_KEY}"
    
    # 요청 본문 구성 (LlmService.java의 GeminiApiRequest 구조 참고)
    request_body = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "temperature": config.GEMINI_TEMPERATURE
        }
    }
    
    # HTTP 헤더 설정
    headers = {
        "Content-Type": "application/json"
    }
    
    # API 호출
    response = _session.post(
        full_url,
        headers=headers,
        data=json.dumps(request_body),
        timeout=config.LLM_TIMEOUT
    )
    
    response.raise_for_status()
    return response.json()

def _extract_first_candidate_text(gemini_response: dict) -> str:
    """Gemini 응답에서 첫 번째 후보 텍스트 추출 (LlmService.java 로직 참고)"""
    try:
        candidates = gemini_response.get("candidates", [])
        if not candidates:
            raise ValueError("No candidates in response")
        
        first_candidate = candidates[0]
        content = first_candidate.get("content", {})
        parts = content.get("parts", [])
        
        if not parts:
            raise ValueError("No parts in content")
        
        return parts[0].get("text", "")
    except (KeyError, IndexError) as e:
        raise ValueError(f"Failed to extract text from Gemini response: {e}")

def normalize_to_3_sentences(breed: str, colors: str, features: str) -> List[str]:
    """스프링 서버 대신 Gemini API 직접 호출"""
    last_error = None
    
    for attempt in range(config.LLM_MAX_RETRIES):
        try:
            # 1. 프롬프트 생성
            prompt = _generate_gemini_prompt(breed, colors, features)
            
            # 2. Gemini API 호출
            gemini_response = _call_gemini_api(prompt)
            
            # 3. 응답에서 텍스트 추출
            llm_output_text = _extract_first_candidate_text(gemini_response)
            
            if not llm_output_text or llm_output_text.strip() == "":
                raise ValueError("Empty response from Gemini")
            
            # 4. JSON 파싱 (LlmService.java의 parseToLlmResponse 로직 참고)
            cleaned_json = llm_output_text.replace("```json", "").replace("```", "").strip()
            parsed_response = json.loads(cleaned_json)
            
            # 5. 문장들 추출 (응답 포맷: {"sentence1": "...", "sentence2": "...", "sentence3": "..."})
            sentences = [
                parsed_response.get("sentence1", "").strip(),
                parsed_response.get("sentence2", "").strip(),
                parsed_response.get("sentence3", "").strip()
            ]
            
            # 6. 유효성 검증
            sentences = [s for s in sentences if s]
            
            if len(sentences) < 3:
                raise ValueError(f"Insufficient sentences: expected 3, got {len(sentences)}")
            
            return sentences[:3]
            
        except Exception as e:
            last_error = e
            logger.warning(f"Gemini API call failed (attempt {attempt + 1}/{config.LLM_MAX_RETRIES}): {type(e).__name__}: {str(e)}")
            if attempt < config.LLM_MAX_RETRIES - 1:
                time.sleep(1.2 ** attempt)  # 지수 백오프
            continue
    
    # 모든 재시도 실패 시 폴백
    logger.error(f"Gemini API failed after {config.LLM_MAX_RETRIES} attempts. Last error: {type(last_error).__name__}: {str(last_error)}")
    
    cs = ", ".join([c.strip() for c in (colors or "").split(",") if c.strip()])
    s1 = f"A unknown dog"
    s2 = "Appearance summary: unknown"
    s3 = f"{'unknown'}; colors: unknown"
    return [s1, s2, s3]
