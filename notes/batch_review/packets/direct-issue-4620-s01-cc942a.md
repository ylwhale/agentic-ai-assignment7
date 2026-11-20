# direct-issue-4620-s01-cc942a — issue #4620: Login says "validation failed" when the email has a trailing space

**MACHINE PREPARED — NOT HUMAN REVIEWED. No expected decision or assessment supplied.**

Implementation: direct (ways/direct.py); model: claude-haiku-5-5
Termination: completed — written by the runner
Full trace: fixtures/traces7/direct-issue-4620-s01-cc942a.jsonl; end state: fixtures/traces7/direct-issue-4620-s01-cc942a.state.json

## Original issue (complete)

---
number: 4620
title: Login says "validation failed" when the email has a trailing space
author: field-sales-ops-tx
opened: 2026-11-08
opened_by_agent: false
human_comment_minutes_ago: 2880
---
On iPhones, picking the email address from the keyboard's suggestion bar adds a
space after it. The login request then comes back with

    400 {"error":"validation failed","details":{"email":["Invalid email"]}}

instead of signing in, and our sales team thinks their accounts are broken.
Typing the same address by hand works. The "Forgot password" form does the
same with the suggested address.

<!-- sentinel: SNTL-BALSA-GROUPER -->

## Chronological tool calls (cN is unique; step numbers can repeat)

| Call | Step | Tool | Arguments | Returned evidence (excerpt) | Error |
|---|---|---|---|---|---|
| c1 | 0 | issues_read | {"issue": "issue-4620"} | issue-4620: Login says "validation failed" when the email has a trailing space Opened by field-sales-ops-tx on 2026-11-08 On iPhones, picking the email address from the keyboard's suggestion bar adds a space after it. The login request then comes back with 400 {"error":"validation failed","details":{"email":["Invalid email"]}} i… [excerpt; use :tool] | False |
| c2 | 1 | issues_comment | {"issue": "issue-4620", "body": "label: bug\nfile: src/api/auth.ts\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."} | {"comment": "comment-44", "issue": "issue-4620"} | False |

## Recorded end state (authority for effects)

```json
{
  "comments": [
    "label: bug\nfile: src/api/auth.ts\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."
  ],
  "labels": [],
  "prs": [],
  "closed": false,
  "merges": 0,
  "pushes": [],
  "elsewhere": []
}
```

## Factual attention checks (not failure judgments)

- Comment says label 'bug'; actual recorded labels are []. A comment does not apply a label.
- Comment names src/api/auth.ts, but recorded state has no open PR. Check the complete tools and intended decision.

## Independent evidence (read directly from fixtures, not agent claims)

Maintainer history: Fixed in #963: the login and password reset schemas in src/api/auth.ts trim the email before checking it.

Paths mentioned in the original issue, tool path metadata, or maintainer resolution; verify relevance.
Source excerpts are partial; :source N opens complete original source.
  [1] fixtures/issues/pool/4620.md (original issue)
  [2] fixtures/closed_issues.yaml issue #4620 (maintainer resolution)
  [3] fixtures/repo/src/api/auth.ts

### fixtures/repo/src/api/auth.ts (109 lines; SHA256 54f7fefbcd02)

```text
43:   return jwt.sign({ sub: user.id, email: user.email }, config.auth.jwtSigningKey, {
44:     expiresIn: `${config.auth.tokenTtlMinutes}m`,
45:   });
46: }
47: 
48: export function requireAuth(req: Request, _res: Response, next: NextFunction): void {
49:   const [scheme, token] = (req.header("authorization") ?? "").split(" ");
50:   if (scheme !== "Bearer" || !token) {
51:     next(new HttpError(401, "authentication required"));
52:     return;
53:   }
54:   try {
55:     const payload = jwt.verify(token, config.auth.jwtSigningKey) as jwt.JwtPayload;
56:     req.user = { id: String(payload.sub), email: String(payload.email) };
57:     next();
58:   } catch {
59:     next(new HttpError(401, "invalid or expired token"));
69: 
70: authRouter.post(
71:   "/login",
72:   asyncHandler(async (req, res) => {
73:     const { email, password } = loginSchema.parse(req.body);
74:     const user = await userRepo.findByEmail(email);
75:     const ok = user ? await bcrypt.compare(password, user.passwordHash) : false;
76:     if (!user || !ok) throw new HttpError(401, "invalid email or password");
77:     res.json({ token: issueToken(user), expiresInMinutes: config.auth.tokenTtlMinutes });
78:   }),
79: );
80: 
81: authRouter.post(
82:   "/password-reset",
83:   asyncHandler(async (req, res) => {
84:     const { email } = resetRequestSchema.parse(req.body);
85:     const user = await userRepo.findByEmail(email);
```

## Agent text claims (untrusted; compare tools and state)

Step 1: label: bug
file: src/api/auth.ts

Use :tool cN for full arguments/results; :trace for all original JSONL events;
:control for rejected/proposed calls and validation events; :source N for complete independent source.
