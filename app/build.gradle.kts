plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "kr.incar.base"
    compileSdk = 35
    // 차량 속도용 안드로이드 오토모티브 표준 Car API
    useLibrary("android.car")

    defaultConfig {
        applicationId = "kr.incar.base"
        minSdk = 28
        targetSdk = 35
        // 갤럭시 탭 시연용 설치 파일: ./gradlew assembleDebug -Ptablet
        manifestPlaceholders["automotiveRequired"] = if (project.hasProperty("tablet")) "false" else "true"
        versionCode = 1
        versionName = "0.1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            // 공모전 제출용 release APK도 바로 설치되도록 디버그 키로 서명한다
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
    }
    // 안내 음성 파일은 압축하지 않아야 바로 열어 재생할 수 있다
    androidResources {
        noCompress += "wav"
    }
}

dependencies {
    implementation(libs.vehicle.sdk)
    implementation(libs.navi.helper)
    implementation(libs.pleos.stt)

    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.material3)
}
