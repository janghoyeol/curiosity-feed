# 0004. 배포 플랫폼

## 상태

승인됨 (2026-10-28)

## 결정

**Fly.io**에 Docker 컨테이너로 배포한다.

이유:

- ADR 0003에서 스케줄러(APScheduler)를 같은 프로세스 안에서 돌리기로
  했기 때문에, 요청이 없을 때 컨테이너를 재우는 서버리스 플랫폼(예:
  Vercel류)은 쓸 수 없다. 스케줄러가 매일 돌려면 프로세스가 계속
  떠 있어야 한다.
- SQLite 파일을 영구 보존해야 해서 persistent volume이 필요하다.
  Fly는 `fly volumes create`로 간단히 만들 수 있다.
- 무료 티어가 상대적으로 가볍고, `fly deploy` 한 줄로 배포할 수 있어
  "가볍게 가자"는 기존 방향과 맞는다.

## 알려진 비용 트레이드오프

`auto_stop_machines = false` + `min_machines_running = 1`로 설정해서
머신이 항상 떠 있게 했다. 이건 스케줄러가 매일 돌려면 필요한 설정이지만,
요청이 없을 때도 꺼지지 않으니 트래픽이 거의 없는 기간에는 "스케일투제로"
앱보다 무료 할당량을 더 많이 쓴다. 비용이 부담되면 스케줄러를 별도
워커 프로세스로 분리하고 웹 서비스는 스케일투제로로 돌리는 구조로
바꿀 수 있는데, 지금 단계에서는 오버엔지니어링이라 보류.

## 배포 절차

```bash
# 1. flyctl 설치 (이미 설치돼 있으면 생략)
curl -L https://fly.io/install.sh | sh

# 2. 로그인 (브라우저로 진행됨)
fly auth login

# 3. 앱 생성 (이름이 이미 쓰이고 있으면 fly.toml의 app 값을 바꿔야 함)
fly apps create curiosity-feed

# 4. SQLite용 영구 볼륨 생성 (1GB면 충분)
fly volumes create curiosity_feed_data --region nrt --size 1

# 5. 비밀값 등록 (절대 fly.toml이나 git에 커밋하지 않음)
fly secrets set \
  GROQ_API_KEY=... \
  DATA_GO_KR_FIRE_SERVICE_KEY=... \
  NAVER_CLIENT_ID=... \
  NAVER_CLIENT_SECRET=...

# 6. 배포
fly deploy
```

배포 후 `https://<앱이름>.fly.dev`에서 바로 피드를 볼 수 있다.
