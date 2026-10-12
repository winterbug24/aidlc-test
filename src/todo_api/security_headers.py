"""모든 응답에 붙이는 보안 헤더와 캐시 헤더."""

from __future__ import annotations

from flask import Flask

# 기본은 모두 차단하고 같은 출처의 스크립트, 스타일, API 호출만 허용한다.
# 인라인 스크립트/스타일과 eval은 허용하지 않는다.
CSP_DIRECTIVES: tuple[tuple[str, str], ...] = (
    ("default-src", "'none'"),
    ("script-src", "'self'"),
    ("style-src", "'self'"),
    ("connect-src", "'self'"),
    # data:는 브라우저가 아이콘 파일을 따로 요청하지 않게 하는 빈 아이콘 선언용이다.
    ("img-src", "'self' data:"),
    ("base-uri", "'none'"),
    ("form-action", "'none'"),
    ("frame-ancestors", "'none'"),
)
CONTENT_SECURITY_POLICY = "; ".join(f"{name} {value}" for name, value in CSP_DIRECTIVES)

RESPONSE_HEADERS: dict[str, str] = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    # 루프백 HTTP에서는 브라우저가 무시한다. HTTPS 뒤에 둘 때를 위해 보낸다.
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Cache-Control": "no-store",
}


def register_security_headers(app: Flask) -> None:
    """화면 파일, API 응답, 오류 응답을 가리지 않고 같은 헤더를 붙인다."""

    @app.after_request
    def apply_security_headers(response):
        for name, value in RESPONSE_HEADERS.items():
            response.headers[name] = value
        return response
