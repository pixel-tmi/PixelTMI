package kr.incar.base.tmi

/**
 * 말 한마디를 명령으로 바꾼다 — 부르는 말(호출어) 없이 바로 ("다음 트랙"처럼).
 * "제보" → 제보 시작? / "1차로 포트홀" → 제보 접수 / "아직 있어"·"없어졌어" → 지나간 위험 확인 / "TMI" → 브리핑 / "TMI 꺼"·"TMI 켜"
 * "음소거" → 소리만 끄기 (말풍선은 그대로) / "음소거 해제"·"소리 켜" → 다시 켜기 / "소리 크게"·"소리 작게" → 20%씩
 */
sealed interface VoiceCommand {
    data object Briefing : VoiceCommand
    /** "잠실역 가자" · "롯데월드타워로 안내해 줘" → 길안내 */
    data class Navigate(val place: String) : VoiceCommand
    /** weak = 평소 대화에도 나오는 말로만 맞춘 것 → "제보" 뒤나 차로를 붙였을 때만 접수 */
    data class Report(val type: HazardType, val lane: Int?, val weak: Boolean = false) : VoiceCommand
    data object StartReport : VoiceCommand
    data object Mute : VoiceCommand
    data object Louder : VoiceCommand
    data object Quieter : VoiceCommand
    data object Unmute : VoiceCommand
    data object StillThere : VoiceCommand
    data object Gone : VoiceCommand
    data object TurnOff : VoiceCommand
    data object TurnOn : VoiceCommand
    data object Unknown : VoiceCommand
    /** "리셋 · 지워줘 · 클리어" — 내 제보 표시 지우기 (한 번 더 물어본다) */
    data object Reset : VoiceCommand
    /** 공유하지 않는 제보 (예: 음주단속 위치) — 이유를 말해 준다 */
    data class Refuse(val why: String) : VoiceCommand

    companion object {
        /**
         * 상황별로 사람들이 실제로 하는 말. 위에서부터 먼저 맞춘다 (겹치는 말은 구체적인 쪽이 위).
         * 첫째 목록 = 딱 그 뜻인 말 → 바로 접수. 둘째 목록 = 평소 대화에도 나오는 말("연기", "막혀", "사고 싶다")
         * → "제보"라고 먼저 말했거나 "2차로"처럼 차로를 붙였을 때만 접수 (계속 듣기라 잘못 접수되지 않게).
         */
        private val keywords: List<Triple<HazardType, List<String>, List<String>>> = listOf(
            Triple(HazardType.WILDFIRE, listOf("산불"), listOf("산에 불", "산이 타")),
            Triple(HazardType.AVALANCHE, listOf("눈사태"), emptyList()),
            Triple(HazardType.TSUNAMI, listOf("해일", "쓰나미"), listOf("파도가 넘", "파도가 도로", "너울")),
            Triple(HazardType.SIGNAL, listOf("신호등 고장", "신호 고장", "신호등이 고장"), listOf("신호등 꺼", "신호등이 꺼", "신호가 안 들어", "신호등이 안", "점멸 신호")),
            Triple(HazardType.WRONG_WAY, listOf("역주행"), listOf("거꾸로 오", "거꾸로 달", "반대로 달", "반대 방향으로 오")),
            Triple(HazardType.EMERGENCY, listOf("구급차", "앰뷸런스", "엠뷸런스", "엠블런스", "응급차", "소방차", "긴급차"), listOf("사이렌", "경찰차", "119")),
            Triple(HazardType.FIRE, listOf("화재", "차에 불", "차량 화재"), listOf("불났", "불이 났", "불 났", "불타", "불길", "연기", "차가 타")),
            Triple(HazardType.ROCKFALL, listOf("낙석", "산사태", "토사 유출", "흙이 쏟아", "흙더미"), listOf("돌 떨어", "돌이 떨어", "돌이 굴러", "토사", "바위")),
            // 여름 장마·태풍: 침수·범람·홍수·물에 잠김은 모두 같은 위험
            Triple(HazardType.FLOOD, listOf("침수", "범람", "홍수", "물웅덩이", "물에 잠", "도로가 잠", "길이 잠", "하천이 넘", "강이 넘", "개울이 넘", "물바다", "물이 넘쳐"),
                listOf("물이 고", "물이 차", "잠겼", "물 넘", "물이 넘", "물이 많", "빗물이")),
            Triple(HazardType.HAIL, listOf("우박"), emptyList()),
            Triple(HazardType.SNOW, listOf("폭설", "함박눈", "눈보라", "눈 온다", "눈이 온다", "눈이 와", "눈 와", "눈 내려", "눈이 내려", "눈길", "눈이 많이", "눈 많이"), listOf("눈이 쌓", "눈 쌓")),
            Triple(HazardType.RAIN, listOf("소나기", "폭우", "장대비", "집중호우", "호우", "장마", "비가 퍼부", "비 퍼부", "비 온다", "비가 온다", "비가 와", "비 와", "비 내려", "비가 내려", "빗길", "비가 쏟아", "비 쏟아", "비가 많이", "비 많이"), listOf("물폭탄")),
            Triple(HazardType.WIND, listOf("강풍", "돌풍", "태풍"), listOf("바람이 세", "바람 세", "바람이 많이", "바람 많이", "날아갈 것")),
            // 가을 안개·봄 황사: 앞이 안 보이는 건 모두 '시야 나쁨'
            Triple(HazardType.FOG, listOf("안개", "해무", "물안개", "황사", "미세먼지"), listOf("앞이 안 보", "시야가 안", "시야가 나", "뿌옇", "희뿌")),
            Triple(HazardType.ANIMAL, listOf("고라니", "멧돼지", "로드킬"), listOf("사슴", "너구리", "동물", "강아지", "개가", "고양이가", "새가")),
            Triple(HazardType.PEDESTRIAN, listOf("보행자", "무단횡단"), listOf("사람이 건너", "사람이 지나", "사람이 걸어", "자전거", "킥보드", "아이가", "어린이가", "할머니", "할아버지")),
            Triple(HazardType.BREAKDOWN, listOf("고장차", "고장 차량", "퍼진 차"), listOf("고장", "퍼졌", "멈춘 차", "서 있는 차", "비상등", "견인", "갓길에 차", "정차 차량")),
            Triple(HazardType.ROAD_CLOSED, listOf("도로 통제", "진입 금지", "통행 금지"), listOf("통제", "차단", "길을 막", "도로를 막", "막아 놨")),
            Triple(HazardType.ACCIDENT, listOf("사고 났", "교통사고", "사고 현장", "추돌", "충돌", "전복"), listOf("사고", "접촉", "박았", "부딪", "뒤집")),
            Triple(HazardType.CONSTRUCTION, listOf("공사 중", "공사중", "도로 공사", "공사 구간", "공사장", "공사 해", "공사해", "공사하"), listOf("공사", "작업 중", "도로 보수", "차로 막", "라바콘", "고깔")),
            Triple(HazardType.POTHOLE, listOf("포트홀", "포트 홀", "포토홀", "포토 홀", "싱크홀", "땅꺼짐", "땅이 꺼", "도로 구멍", "도로에 구멍", "침하", "도로가 꺼", "길이 꺼", "내려앉"),
                listOf("구멍", "패인", "파인", "움푹", "도로 파손", "꺼졌")),
            Triple(HazardType.DEBRIS, listOf("낙하물", "적재물", "타이어 조각", "장애물", "떨어진 물건", "도로에 뭐가", "길에 뭐가", "나뭇가지", "쓰러진 나무"),
                listOf("떨어진", "떨어져 있", "물건", "박스", "짐이 떨어", "쓰레기", "뭐가 떨어", "낙엽")),
            // 겨울: 얼었어·결빙·길이 얼었어·살얼음은 모두 결빙
            Triple(HazardType.ICE, listOf("결빙", "빙판", "블랙아이스", "블랙 아이스", "살얼음", "얼었", "얼어 있", "얼어붙", "길이 얼", "도로가 얼", "노면이 얼", "다리 위가 얼"),
                listOf("얼음", "미끄", "꽁꽁", "얼어")),
            Triple(HazardType.JAM, listOf("정체"), listOf("막혀", "밀려", "차가 많", "거북이", "꽉 막")),
        )

        /** 음성 인식이 "TMI"를 받아 적는 여러 모양 */
        private val TMI_WORDS = listOf("tmi", "티엠아이", "티앰아이", "티이엠아이", "팀아이")

        private val laneWords = mapOf(
            "1" to 1, "일" to 1, "첫" to 1, "2" to 2, "이" to 2, "두" to 2,
            "3" to 3, "삼" to 3, "세" to 3, "4" to 4, "사" to 4, "네" to 4,
        )
        private val laneRegex = Regex("""(\d|일|이|삼|사|첫|두|세|네)\s*(?:번째|번)?\s*차(?:로|선)""")

        /** "(TMI/티미야) 잠실역(으로/까지) 가자 · 가 줘 · 안내해 줘 · 길 찾아 줘 · 찍어 줘 · 데려다 줘 · 가는 길 알려 줘" */
        private val navRegex = Regex(
            """^((?:tmi|티엠아이|티앰아이|티이엠아이|팀아이|티\s*엠\s*아이|티미)(?:야|아)?[,\s]*)?(.+?)\s*(까지|으로|로)?\s*""" +
                """(?:가자|가\s*줘|가\s*주세요|가\s*줄래|안내\s*(?:해\s*)?(?:줘|주세요|해|시작)|길\s*안내\s*(?:해\s*)?(?:줘|주세요)?|""" +
                """길\s*찾아\s*(?:줘|주세요)|가는\s*길\s*(?:알려|안내해)\s*(?:줘|주세요)|찍어\s*(?:줘|주세요)|데려다\s*(?:줘|주세요|줄래))$""",
            RegexOption.IGNORE_CASE,
        )
        /** 이런 말이 섞이면 장소가 아니라 대화 ("집에 가자", "빨리 가자") → TMI를 불렀을 때만 길안내 */
        private val CHAT_WORDS = setOf("집에", "빨리", "얼른", "어서", "이제", "그냥", "같이", "다시", "천천히", "조심히", "먼저", "일단", "우리", "나", "좀", "밥", "놀러", "어디", "여기", "저기", "거기")

        /** 지금 펫 이름 (이름으로 불러도 알아듣게 — "호두야, 잠실역 가자") */
        @Volatile var petName = "티미"

        fun parse(raw: String): VoiceCommand {
            var clean = raw.trim().trimEnd('.', '!', '?', '~', '。')
            // 펫 이름으로 부른 건 TMI로 부른 것과 같다
            val nm = petName
            for (call in listOf("${nm}야", "${nm}아", nm)) if (nm.isNotBlank() && clean.startsWith(call)) { clean = "TMI " + clean.removePrefix(call).trimStart(',', ' '); break }
            navRegex.find(clean)?.let { m ->
                val woke = m.groupValues[1].isNotBlank()
                var place = m.groupValues[2].trim().trimEnd(',', '.')
                // 받침(ㄹ 제외) 뒤의 '로'는 조사가 아니라 이름의 일부: 종로 · 테헤란로
                val last = place.lastOrNull()
                if (m.groupValues[3] == "로" && last != null && last in '가'..'힣' && (last - '가') % 28 !in setOf(0, 8)) place += "로"
                val chatty = place.split(' ').any { it in CHAT_WORDS } || place.endsWith("러")
                if (place.length in 2..30 && (woke || !chatty)) return Navigate(place)
            }
            // 이름만 불렀으면("티미야") 브리핑
            if (clean.startsWith("TMI ") && clean.removePrefix("TMI").isBlank() && !raw.lowercase().contains("tmi")) return Briefing
            val t = raw.replace(" ", "").lowercase()
            // "음소거" → 소리만 끄기 ("음소거 해제"·"소리 켜" → 다시 켜기). 해제를 먼저 본다
            if (listOf("음소거해제", "음소거풀어", "소리켜", "소리다시").any { it in t }) return Unmute
            if (listOf("음소거", "소리꺼", "소리끄").any { it in t }) return Mute
            if (listOf("소리크게", "소리키워", "볼륨업", "볼륨올려", "크게해").any { it in t }) return Louder
            if (listOf("소리작게", "소리줄여", "볼륨다운", "볼륨내려", "작게해").any { it in t }) return Quieter
            if (TMI_WORDS.any { "${it}꺼" in t || "${it}그만" in t }) return TurnOff
            if (TMI_WORDS.any { "${it}켜" in t }) return TurnOn
            // 리셋·지워줘·클리어 → 내 제보 표시 지우기 (엔진이 한 번 더 묻는다)
            if (listOf("리셋", "지워줘", "지워주세요", "지워라", "다지워", "클리어", "초기화", "삭제해").any { it in t }) return Reset
            // 음주단속·검문 위치는 공유하지 않는다 (단속 회피를 돕지 않음)
            if (listOf("음주단속", "음주 단속", "검문", "단속하", "단속 중", "단속중").any { it.replace(" ", "") in t })
                return Refuse("음주단속·검문 위치는 공유하지 않아요\n안전운전이 최고의 TMI!")
            fun hit(words: List<String>) = words.any { it.replace(" ", "") in t }
            val strong = keywords.firstOrNull { (_, sure, _) -> hit(sure) }
            val found = strong ?: keywords.firstOrNull { (_, _, maybe) -> hit(maybe) }
            if (found != null) {
                val lane = if ("갓길" in t) 0 else laneRegex.find(raw)?.groupValues?.get(1)?.let { laneWords[it] }
                return Report(found.first, lane, weak = strong == null)
            }
            if (listOf("없어", "없네", "치웠", "해결", "사라졌").any { it in t }) return Gone
            if (listOf("아직있", "있어", "그대로", "있네").any { it in t }) return StillThere
            if (listOf("제보", "신고").any { it in t }) return StartReport
            // "TMI" 한마디면 충분 — 늘 듣고 있으니 "알려줘"·"어때" 같은 흔한 말은 넣지 않는다 (대화 중 잘못 켜짐 방지)
            if (TMI_WORDS.any { it in t }) return Briefing
            return Unknown
        }
    }
}
