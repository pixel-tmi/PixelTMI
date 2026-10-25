# Pixel TMI (픽셀 TMI)

운전하다 본 위험을 **말 한마디로 제보**하고, 차 화면 아래를 달리는 **도트 펫**이 앞길 위험을 미리 알려 주는
"차들이 함께 만드는 도로 TMI" 앱입니다. (현대자동차그룹 차량용 앱 개발 공모전 · Pleos Connect)

## APK
| 파일 | 용도 |
|---|---|
| [`apk/PixelTMI_PixelTMI_release.apk`](apk/PixelTMI_PixelTMI_release.apk) | **Pleos Connect** (Android Automotive) 차량·에뮬레이터용 |
| [`apk/PixelTMI_PixelTMI_tablet_release.apk`](apk/PixelTMI_PixelTMI_tablet_release.apk) | 일반 안드로이드 태블릿 시연용 (Pleos 화면 그림 위에서 가상 차량으로 시연) |

두 파일 모두 바로 설치되도록 release 빌드를 디버그 키로 서명했습니다.

## 시연 영상
- [`video/Pixel_TMI_시연영상.mp4`](video/Pixel_TMI_시연영상.mp4) — 갤럭시 탭 Pleos 화면 시연 녹화 (약 2분): 출근길 브리핑 → 위험 접근 → 말로 제보 → 위험 컷인 → 도착 세레모니

## 실행 방법
### Pleos Connect 에뮬레이터 (권장)
1. Android Studio → SDK Manager에 Pleos 이미지 주소를 추가하고 **Pleos Connect v2.1.0 (API 34)** 에뮬레이터를 만듭니다.
2. `adb install apk/PixelTMI_PixelTMI_release.apk`
3. 앱 목록에서 **Pixel TMI** 실행 → 마이크·위치·알림 권한 허용 → 화면 아래에 펫과 버튼(소리·브리핑·말하기·설정)이 나타납니다.
4. 설정(톱니) → **시연 · 주행 → ▶ 출근길 시연** 을 누르면 실제 운전 없이 위험 제보·공유·확인·도착 세레모니까지 한 번에 볼 수 있습니다.

### 일반 태블릿
1. `adb install apk/PixelTMI_PixelTMI_tablet_release.apk`
2. **Pixel TMI** 아이콘 → Pleos 화면 그림이 열립니다. 그림 속 버튼(P/D 기어, 전조등, 와이퍼, 공조, 내비)이 가상 차량을 움직이고 펫이 반응합니다.
3. 가운데 내비 카드 **목적지 입력 → ▶ 모의 주행** 으로 길안내 시연, **Pixel TMI 지도** 아이콘은 네이버 지도·카카오맵·티맵 위에 펫을 띄웁니다.

### 말로 제보해 보기
말하기 버튼(또는 항상 듣기)을 켜고 "2차로 포트홀", "앞에 사고 났어", "소나기 와요", "공사 중이야" 처럼 말하면 됩니다.

## 테스트 환경 및 필요한 설정
- Android Studio (Koala 이상), Gradle 8+, JDK 17, Kotlin, minSdk 28 / targetSdk 34
- 사용 SDK: Pleos **Vehicle**(차량 상태: 기어·속도·와이퍼·전조등 등), **NaviHelper**(차량 내비 목적지·안내 연동)
- 준비 중인 SDK(FusedLocation·TextToSpeech·SpeechToText·Vehicle Control)는 기기 기본 위치·음성 인식으로 대신 동작합니다.
- 날씨: Open-Meteo(기상청 KMA 모델, 키 없음) — 인터넷 연결 필요
- 빌드: `./gradlew :app:assembleRelease` (차량용) · `./gradlew :app:assembleRelease -Ptablet` (태블릿용)

## 안전 설계
- 주행 중에는 글자 입력·상점·대부분의 설정을 막고 **말로만** 조작합니다.
- 경고는 짧은 울음 + 말풍선 하나로, 펫의 동작·고증 TMI는 **정차(P) 중에만** 나옵니다.
- 코인은 내 제보를 **다른 차들이 확인했을 때만** 쌓입니다.

## 폴더
- `app/` 안드로이드 앱 소스 (Kotlin) · `app/src/main/assets/pet/` 도트 캐릭터·소품·위험 표시
- `도구/` 도트 그림·울음소리를 코드로 만드는 스크립트 (Python + Pillow)

데이터 출처: 날씨 Open-Meteo.com (CC BY 4.0) · 글꼴 Galmuri (SIL OFL 1.1)
