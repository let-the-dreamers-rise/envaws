/* Staff sign-in against Amazon Cognito (USER_PASSWORD_AUTH over the public IdP API, no SDK).
   Locally (no CLEANHOUR_AUTH in config.js) the dev server accepts a demo role instead. */
window.CHAuth = (() => {
  const cfg = window.CLEANHOUR_AUTH || null;
  const KEY = "cleanhour.session";
  const ROLE_KEY = "cleanhour.demoRole";
  let memory = null;
  const read = (k) => { try { return sessionStorage.getItem(k); } catch (e) { return null; } };
  const write = (k, v) => { try { v == null ? sessionStorage.removeItem(k) : sessionStorage.setItem(k, v); } catch (e) { /* private mode */ } };
  const session = {
    get() { try { return JSON.parse(read(KEY)) || memory; } catch (e) { return memory; } },
    set(v) { memory = v; write(KEY, v ? JSON.stringify(v) : null); },
  };

  async function cognito(target, body) {
    const res = await fetch(`https://cognito-idp.${cfg.region}.amazonaws.com/`, {
      method: "POST",
      headers: { "content-type": "application/x-amz-json-1.1", "x-amz-target": `AWSCognitoIdentityProviderService.${target}` },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.message || "Sign-in failed");
    return data;
  }

  function claims(token) {
    const part = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = part + "=".repeat((4 - (part.length % 4)) % 4);
    return JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(padded), (c) => c.charCodeAt(0))));
  }

  function save(result, refresh) {
    session.set({ id: result.IdToken, refresh: result.RefreshToken || refresh, exp: claims(result.IdToken).exp * 1000 });
  }

  async function signIn(email, password) {
    const r = await cognito("InitiateAuth", { AuthFlow: "USER_PASSWORD_AUTH", ClientId: cfg.clientId, AuthParameters: { USERNAME: email, PASSWORD: password } });
    if (!r.AuthenticationResult) throw new Error("This account needs a new password. Ask your district admin.");
    save(r.AuthenticationResult);
  }

  async function token() {
    const s = cfg && session.get();
    if (!s) return null;
    if (Date.now() < s.exp - 60000) return s.id;
    try {
      const r = await cognito("InitiateAuth", { AuthFlow: "REFRESH_TOKEN_AUTH", ClientId: cfg.clientId, AuthParameters: { REFRESH_TOKEN: s.refresh } });
      save(r.AuthenticationResult, s.refresh);
      return session.get().id;
    } catch (e) { session.set(null); return null; }
  }

  async function headers() {
    if (!cfg) return { "x-demo-user": read(ROLE_KEY) || "principal" };
    const t = await token();
    return t ? { authorization: `Bearer ${t}` } : {};
  }

  const DEMO = [
    ["principal@demo-rohini.cleanhour.in", "Principal", "approves the plan"],
    ["pe.teacher@demo-rohini.cleanhour.in", "PE teacher", "views and asks, can't approve"],
    ["district.admin@cleanhour.in", "District admin", "adds schools"],
  ];

  // A small modal; resolves once signed in.
  function dialog(message) {
    return new Promise((resolve) => {
      const wrap = document.createElement("div");
      wrap.className = "auth-backdrop";
      wrap.innerHTML = `<form class="auth-card card" aria-labelledby="authTitle">
        <h2 id="authTitle">Staff sign-in</h2>
        <p class="note">${message || "Principals approve plans. Teachers view and ask. Parents need no account."}</p>
        <label>Email<input class="field" name="email" type="email" autocomplete="username" required></label>
        <label>Password<input class="field" name="password" type="password" autocomplete="current-password" required></label>
        <p class="auth-error" role="alert"></p>
        <button class="btn primary block" type="submit">Sign in</button>
        ${cfg && cfg.demoPassword ? `<p class="note" style="margin-top:12px">Demo accounts (password <code>${cfg.demoPassword}</code>):</p>
          <div class="suggest">${DEMO.map(([e, r, d]) => `<button type="button" data-email="${e}" title="${d}">${r}</button>`).join("")}</div>` : ""}
      </form>`;
      document.body.appendChild(wrap);
      const form = wrap.querySelector("form");
      form.email.focus();
      wrap.querySelectorAll("[data-email]").forEach((b) => b.addEventListener("click", () => {
        form.email.value = b.dataset.email; form.password.value = cfg.demoPassword; form.requestSubmit();
      }));
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = form.querySelector("button[type=submit]");
        btn.disabled = true; btn.textContent = "Signing in…";
        try { await signIn(form.email.value.trim(), form.password.value); wrap.remove(); resolve(); }
        catch (err) { form.querySelector(".auth-error").textContent = err.message; btn.disabled = false; btn.textContent = "Sign in"; }
      });
    });
  }

  async function ensure(message) {
    if (cfg && !(await token())) await dialog(message);
  }

  function signOut() { session.set(null); location.reload(); }
  function setDemoRole(role) { write(ROLE_KEY, role); location.reload(); }
  const demoRole = () => read(ROLE_KEY) || "principal";

  return { enabled: !!cfg, ensure, dialog, headers, signOut, setDemoRole, demoRole };
})();
