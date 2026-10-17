# 작동 방식

[English](HOW_IT_WORKS.md) | **한국어**

> 기준 문서는 영어 원문인 [HOW_IT_WORKS.md](HOW_IT_WORKS.md)입니다.

이 문서는 HSA 영수증 검토의 구조, 구성 요소별 역할, 데이터 흐름, MCP 동작 방식을 설명합니다.

## 구성 요소별 역할 (누가 무엇을 하는가)

| 구성 요소 | 역할 | 담당 업무 |
|---|---|---|
| **사용자** | 결정권자 | Amazon에 한 번 로그인하고, 실제 도구 실행을 승인하고, 웹 대시보드에서 적격 여부를 검토하고, 청구 내보내기를 승인합니다. |
| **LLM 에이전트** | 작업 진행 | 채팅(Claude Code, Cursor, Gemini 등)으로 대화하며 읽기 전용 도구를 호출하고, IRS 규정에 따라 항목별 적격 여부 메모 초안을 작성하고, 파일을 정리합니다. |
| **MCP 서버** (`amazon-orders-mcp`) | 데이터 수집 | 읽기 전용 Python 서비스입니다. 본인 컴퓨터에 저장된 세션으로 Amazon 주문 내역, 품목, 인보이스 PDF를 안전하게 가져오는 MCP 도구를 제공합니다. |
| **검토 대시보드** (`review.html`) | 화면 | Chrome/Edge에서 바로 실행되는 순수 HTML/JS 페이지입니다. Python 없이 브라우저의 폴더 접근 기능으로 본인의 로컬 데이터 폴더를 읽고 씁니다. |

## 데이터 흐름도

```text
 1. 로그인 (사용자)
    └── Chromium 창에서 Amazon에 한 번 로그인하면 세션 쿠키가 ~/.amazon-orders-mcp/에 저장됩니다

 2. 데이터 수집 (LLM + MCP 서버)
    ├── 사용자가 요청 묶음마다 승인합니다
    ├── MCP 서버가 주문 페이지를 읽고 인보이스 PDF를 <data folder>/<year>/receipts/에 내려받습니다
    └── 사용자가 진료비 청구서, 약국 영수증, EOB를 receipts/에 넣습니다

 3. 분류 및 초안 작성 (LLM)
    ├── LLM이 IRS Publication 502 기준으로 항목을 확인합니다
    └── 처리한 주문 데이터를 <data folder>/<year>/_app/data.json에 씁니다

 4. 검토 및 결정 (검토 대시보드, Python 불필요)
    ├── 사용자가 Chrome이나 Edge에서 review.html을 바로 엽니다
    ├── 페이지가 브라우저의 File System 접근 기능으로 로컬 데이터 폴더에 연결합니다
    ├── 상태를 적격, 부적격, 의사 소견서 / LMN 중에서 정합니다
    └── 선택한 내용이 <data folder>/<year>/decisions.json에 자동 저장됩니다

 5. 내보내기 (브라우저)
    └── 세금 신고용 청구 보고서 PDF, 의료 증빙 PDF, CSV를 만듭니다
```

## MCP(Model Context Protocol) 동작 방식

Amazon MCP 서버(`mcp/amazon-orders/`)는 표준 [Model Context Protocol](https://modelcontextprotocol.io) 서버로, 로컬에서 실행됩니다.

- **세션 처리:** 서버는 `~/.amazon-orders-mcp/cookies.json`에 저장된, 로그인된 Amazon 세션을 사용합니다. 비밀번호는 저장하지 않습니다.
- **읽기 전용 동작:** 도구는 주문 목록, 주문 상세, 상품 배지만 읽어 옵니다. 서버는 주문하거나, 계정 설정을 바꾸거나, 장바구니에 상품을 담을 수 없습니다.
- **제공하는 도구:**
  - `refresh_session`: Chromium을 열어 로그인하게 하고 새 세션을 가져옵니다.
  - `get_order_history(year)`: 지정한 연도의 주문을 읽어 옵니다.
  - `get_order(order_id)`: 품목, 가격, 판매자를 추출하고 인보이스 PDF를 저장합니다.
  - `check_asin_eligibility(asin)`: 로그인 없이 Amazon 상품 공개 페이지에서 "FSA or HSA eligible" 배지가 있는지 확인합니다.
- **안전 장치:** Amazon 주문 페이지에 실제로 접속하려면 최근 1시간 이내에 로그인한 상태여야 합니다(`max_auth_age=3600`). 로그인이 만료되면 작업을 멈추고 세션을 갱신해 달라고 요청합니다.


## 데이터가 있는 곳

데이터는 이 코드 폴더 밖의 데이터 폴더에 있으므로, 코드를 업데이트하거나 다시 내려받아도 데이터는 영향을 받지 않습니다. Amazon 페이지는 화면 없이 실행되는 브라우저와 저장된 세션으로 읽습니다. 결과는 LLM 채팅으로 전달됩니다. 사용자가 확인하면 에이전트가 이를 데이터 폴더 안의 연도 폴더에 씁니다. 검토 페이지는 그 파일을 읽고, 사용자의 결정을 같은 위치에 저장합니다.

| 파일 또는 폴더 | 내용 | 로컬에만 있는가 |
|---|---|---|
| `~/.hsa-review/config.json` | 데이터 폴더의 위치 | 예. |
| `~/.amazon-orders-mcp/` | Amazon 로그인 프로필과 세션 쿠키(비밀번호는 없음) | 예. 절대 공유하지 마세요. |
| `<data folder>/<year>/receipts/` | 본인의 문서. 폴더 한 단계에 모아 두고 `date_type_source_detail` 형식으로 이름을 붙입니다 | 예. 코드 폴더 밖에 있습니다. |
| `<data folder>/<year>/reports/` | 청구 PDF, 증빙 PDF, CSV 내보내기 파일 | 예. |
| `<data folder>/<year>/decisions.json` | 본인의 결정과 메모 | 예. |
| `<data folder>/<year>/_app/` | 주문(`data.json`), `images/`, `product_cache.json`(Amazon 카테고리와 읽은 날짜), `product_decisions.json`(상품별로 정한 내용, 상품 ID 기준), `backups/<date>/`, `logs/`. 직접 편집하는 파일이 아닙니다. | 예. |
| `samples/` (코드 폴더 안) | 같은 구조의 가짜 데이터. 페이지를 시험해 볼 때 사용합니다 | 아니요. 공개 파일입니다. |
| `.agent/` (코드 폴더 안) | 개발자 노트와 임시 작업 파일 | Git에서 제외됩니다. |

## 검토 페이지

- Chrome이나 Edge에서 `review.html`을 더블클릭합니다. 페이지가 데이터 폴더를 한 번 묻고 기억해 두었다가, 연도 폴더 목록을 보여 줍니다(가장 최근 연도를 열며, `?year=2026`으로 지정할 수도 있습니다). 다음에 방문할 때 브라우저가 접근 허용을 다시 물을 수 있습니다.
- 폴더 접근이 안 되는 브라우저(Firefox, Safari)에서는 `python tools/hsa.py open`을 실행하세요. 이 명령은 본인 컴퓨터에서만 접속할 수 있는 작은 서버를 띄우며, 이 서버는 페이지와 데이터 폴더만 제공합니다.
- 연도 폴더를 한 번 선택하면 그 폴더에 결정 내용을 저장합니다. 폴더 접근이 안 되는 Firefox 등의 브라우저에서는 안내 메시지가 나오므로 내보내기(CSV)를 사용하세요.
- 적격 항목마다 **환급 완료** 표시가 있습니다. 합계는 적격 금액을 환급 완료분과 아직 환급받지 않은 금액으로 나눠서 보여 줍니다.
- 연도 데이터 파일의 `YEAR_CONFIG`에서 이월액(`priorUnreimbursed`)과 기준액(threshold)을 정할 수 있습니다. 둘 다 기본값은 0입니다.
- **미환급액**은 회계상의 수치이며 인출할 수 있는 금액이 아닙니다. 인출 가능한 금액은 HSA 잔액과 플랜 규정에 따라 달라집니다.

## 로그

로그 파일은 없습니다. 메시지는 각 도구를 실행한 곳에 나타납니다.

- **MCP 서버:** `Starting ... Server`, `Amazon session expired; opening the sign-in window`, `timed out`, `could not read the page`, 그리고 예상하지 못한 오류의 traceback.
- **스크립트:** 진행 상황이 한 줄씩 나오고, 마지막에 주문별로 `saved`, `skipped`(덮어쓰지 않음), `error`를 요약합니다.
- **검토 페이지:** `2026/hsa_decisions_2026.json에 10:42:05에 저장했습니다`와 같은 상태 줄.
- **개인정보:** 메시지에 주문 번호, 상품 이름, 페이지 본문이 들어 있을 수 있습니다. 공개 이슈에 붙여 넣지 마세요.

## 제한 사항

- Amazon 페이지 구성이 바뀌면 파서를 업데이트하기 전까지 동작하지 않습니다. 오류 메시지에 문제가 된 페이지가 표시됩니다.
- "FSA or HSA eligible" 표시는 판매자 쪽 Amazon의 표시일 뿐 IRS의 판정이 아닙니다. 이 표시를 믿기 전에 상품 페이지를 확인하세요.
- Amazon.com(미국)만 지원합니다.
- 거래 내역 페이지에는 약 10일치만 표시되므로 사용하지 않습니다.

## 의료 증빙 PDF를 인쇄하기 전에

`python tools/check_evidence.py 2026`을 실행하세요. 의료 항목에 이미지가 없거나, PDF의 페이지 수가 이미지보다 많거나, 연도 폴더에 어느 항목에도 속하지 않는 파일이 있으면 실패합니다. 이미지를 불러오지 못할 때는 PDF 버튼도 빈 페이지를 인쇄하지 않고 메시지를 띄우며 멈춥니다.
