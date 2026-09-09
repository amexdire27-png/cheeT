/* cheeT1 landing page — quiet interactions, reduced-motion aware. */
(() => {
  "use strict";

  const q = (sel, root = document) => root.querySelector(sel);
  const qa = (sel, root = document) => [...root.querySelectorAll(sel)];
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

  const player = q("#player");
  const howVideo = q("#howVideo");
  const playerToggle = q("#playerToggle");
  const playerPlayBig = q("#playerPlayBig");
  const playerScrub = q("#playerScrub");
  const playerTime = q("#playerTime");
  const playerChapters = qa("#playerChapters [data-step]");
  const STEP_SEEK = { 1: 0, 2: 3.2, 3: 5.6 };
  let scrubbing = false;

  const stepAt = (t) => {
    if (t < 3.2 || (t >= 11.2 && t < 14.5)) return 1;
    if (t < 5.6 || (t >= 14.5 && t < 15.8)) return 2;
    return 3;
  };

  const fmt = (seconds) => {
    const s = Math.max(0, Math.floor(seconds || 0));
    return `0:${String(s).padStart(2, "0")}`;
  };

  const syncPlayer = () => {
    if (!howVideo) return;
    const t = howVideo.currentTime || 0;
    const dur = Number.isFinite(howVideo.duration) && howVideo.duration > 0
      ? howVideo.duration
      : 25.34;
    const step = stepAt(t);
    playerChapters.forEach((el) => {
      const on = Number(el.dataset.step) === step;
      el.classList.toggle("is-on", on);
      if (on) el.setAttribute("aria-current", "step");
      else el.removeAttribute("aria-current");
    });
    if (playerScrub && !scrubbing) {
      playerScrub.max = String(dur);
      playerScrub.value = String(t);
    }
    if (playerTime) playerTime.textContent = `${fmt(t)} / ${fmt(dur)}`;
    const playing = !howVideo.paused && !howVideo.ended;
    if (playerToggle) {
      playerToggle.textContent = playing ? "Pause" : "Play";
      playerToggle.setAttribute("aria-label", playing ? "Pause" : "Play");
    }
    if (playerPlayBig) {
      playerPlayBig.hidden = playing;
      playerPlayBig.setAttribute("aria-label", playing ? "Pause" : "Play");
    }
  };

  const ensureVideoSrc = () => {
    if (!howVideo || howVideo.getAttribute("src") || !howVideo.dataset.src) return;
    howVideo.src = howVideo.dataset.src;
  };

  const startVideo = () => {
    if (!player || !howVideo) return;
    if (reduced) return;
    ensureVideoSrc();
    howVideo.currentTime = 0;
    syncPlayer();
    howVideo.play().catch(() => {});
  };

  const stopVideo = () => {
    if (!howVideo) return;
    howVideo.pause();
    syncPlayer();
  };

  const toggleVideo = () => {
    if (!howVideo) return;
    if (!howVideo.paused && !howVideo.ended) {
      howVideo.pause();
      syncPlayer();
      return;
    }
    ensureVideoSrc();
    if (howVideo.ended) howVideo.currentTime = 0;
    howVideo.play().catch(() => {});
  };

  if (howVideo) {
    ["timeupdate", "play", "pause", "ended", "loadedmetadata", "seeked"].forEach((ev) => {
      howVideo.addEventListener(ev, syncPlayer);
    });
    howVideo.addEventListener("click", toggleVideo);
  }
  if (playerToggle) playerToggle.addEventListener("click", toggleVideo);
  if (playerPlayBig) playerPlayBig.addEventListener("click", (e) => {
    e.stopPropagation();
    toggleVideo();
  });
  if (playerScrub && howVideo) {
    playerScrub.addEventListener("pointerdown", () => { scrubbing = true; });
    playerScrub.addEventListener("pointerup", () => { scrubbing = false; });
    playerScrub.addEventListener("input", () => {
      ensureVideoSrc();
      howVideo.currentTime = Number(playerScrub.value);
      syncPlayer();
    });
  }
  playerChapters.forEach((el) => {
    el.addEventListener("click", () => {
      if (!howVideo) return;
      ensureVideoSrc();
      howVideo.currentTime = STEP_SEEK[Number(el.dataset.step)] ?? 0;
      syncPlayer();
    });
  });

  const demo = q("#demo");
  if (demo) {
    new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) { stopVideo(); return; }
        startVideo();
      });
    }, { threshold: 0.35 }).observe(demo);
  }

  const acc = q("#acc");
  if (acc) {
    const head = q("#accBtn", acc);
    const panelEl = q("#accPanel", acc);
    head.addEventListener("click", () => {
      const open = head.getAttribute("aria-expanded") !== "true";
      head.setAttribute("aria-expanded", String(open));
      panelEl.hidden = !open;
    });
  }

  const contactBtn = q("#contactBtn");
  const sheet = q("#contactSheet");
  if (contactBtn && sheet) {
    const panel = q(".sheet__panel", sheet);
    const closeBtn = q("#contactClose", sheet);
    let lastFocus = null;

    const focusables = () => qa("a[href], button:not([disabled])", sheet);

    const openSheet = () => {
      lastFocus = document.activeElement instanceof HTMLElement ? document.activeElement : contactBtn;
      sheet.hidden = false;
      contactBtn.setAttribute("aria-expanded", "true");
      document.body.style.overflow = "hidden";
      (panel || closeBtn)?.focus();
    };

    const closeSheet = () => {
      if (sheet.hidden) return;
      sheet.hidden = true;
      contactBtn.setAttribute("aria-expanded", "false");
      document.body.style.overflow = "";
      lastFocus?.focus();
    };

    contactBtn.addEventListener("click", () => {
      if (sheet.hidden) openSheet();
      else closeSheet();
    });
    closeBtn?.addEventListener("click", closeSheet);
    sheet.addEventListener("click", (e) => {
      if (e.target === sheet) closeSheet();
    });
    document.addEventListener("keydown", (e) => {
      if (sheet.hidden) return;
      if (e.key === "Escape") {
        e.preventDefault();
        closeSheet();
        return;
      }
      if (e.key !== "Tab") return;
      const items = focusables();
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && (document.activeElement === first || document.activeElement === panel)) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    });
  }

  const STORE = "cheeT1.community.v1";
  const COMMUNITY_API = (
    location.hostname === "127.0.0.1" || location.hostname === "localhost"
  ) ? "api/community" : "https://cheet1-site.onrender.com/api/community";
  const fmtNum = new Intl.NumberFormat();

  const readLocal = () => {
    try {
      const raw = JSON.parse(localStorage.getItem(STORE) || "null");
      if (raw && typeof raw === "object") return raw;
    } catch {
      /* ignore */
    }
    return {};
  };

  const writeLocal = (data) => {
    localStorage.setItem(STORE, JSON.stringify(data));
  };

  const community = {
    downloads: 0,
    ratingSum: 0,
    ratingCount: 0,
    remote: false,
    ready: false
  };

  const rememberRemote = () => {
    const local = readLocal();
    local.fromRemote = true;
    local.downloads = community.downloads;
    local.ratingSum = community.ratingSum;
    local.ratingCount = community.ratingCount;
    delete local.extraDownloads;
    writeLocal(local);
  };

  const hydrateFromCache = () => {
    const local = readLocal();
    if (!local.fromRemote) return;
    community.downloads = Math.max(0, Number(local.downloads) || 0);
    community.ratingSum = Math.max(0, Number(local.ratingSum) || 0);
    community.ratingCount = Math.max(0, Number(local.ratingCount) || 0);
    community.ready = true;
  };

  const STAR_PATH = "M12 2.2 14.8 8.4 21.6 9.1 16.5 13.6 18 20.5 12 17.1 6 20.5 7.5 13.6 2.4 9.1 9.2 8.4Z";
  const starGlyphs = (n) => {
    const filled = Math.max(0, Math.min(5, Math.round(Number(n) || 0)));
    return Array.from({ length: 5 }, (_, i) => (
      `<svg class="star-icon${i < filled ? " is-on" : ""}" viewBox="0 0 24 24" aria-hidden="true"><path d="${STAR_PATH}"/></svg>`
    )).join("");
  };

  const MAIL_TO = "amexdire27@gmail.com";

  const postCommunity = async (payload) => {
    const res = await fetch(COMMUNITY_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("save failed");
    return res.json();
  };

  const postNoteMail = async ({ name, note, rating }) => {
    const who = name || "Anonymous";
    const stars = `${"★".repeat(rating)}${"☆".repeat(5 - rating)}`;
    const res = await fetch(`https://formsubmit.co/ajax/${MAIL_TO}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        name: who,
        rating: `${stars} (${rating} / 5)`,
        note: note || "(no note)",
        _subject: `cheeT1 note: ${stars} from ${who}`,
        _captcha: "false",
      }),
    });
    if (!res.ok) throw new Error("mail");
  };

  const applyData = (data, remote) => {
    if (!data || typeof data !== "object") return;
    const incomingDown = Math.max(0, Number(data.downloads) || 0);
    let sum = Number(data.rating_sum);
    let count = Number(data.rating_count);
    if (!Number.isFinite(sum) || !Number.isFinite(count) || count < 0) {
      const reviews = Array.isArray(data.reviews) ? data.reviews : [];
      sum = 0;
      count = 0;
      reviews.forEach((r) => {
        const value = Number(r && r.rating);
        if (value >= 1 && value <= 5) {
          sum += value;
          count += 1;
        }
      });
    }
    sum = Math.max(0, sum);
    count = Math.max(0, count);
    community.downloads = incomingDown;
    community.ratingSum = sum;
    community.ratingCount = count;
    community.remote = Boolean(remote);
    community.ready = true;
    if (remote) rememberRemote();
  };

  const renderTally = () => {
    const downloads = community.downloads;
    const sum = community.ratingSum;
    const n = community.ratingCount;
    const avg = n ? sum / n : 0;
    const downloadsEl = q("#tallyDownloads");
    const starsEl = q("#tallyStars");
    const ratingEl = q("#tallyRating");
    const countEl = q("#tallyCount");
    if (downloadsEl) {
      downloadsEl.textContent = community.ready ? fmtNum.format(downloads) : "—";
    }
    if (starsEl) starsEl.innerHTML = starGlyphs(n ? avg : 0);
    if (ratingEl) {
      ratingEl.textContent = n ? (avg).toFixed(1).replace(/\.0$/, "") : "—";
    }
    if (countEl) {
      countEl.textContent = n
        ? `${fmtNum.format(n)} ${n === 1 ? "score" : "scores"}`
        : "No scores yet";
    }
  };

  const paint = () => { renderTally(); };

  const recordDownload = () => {
    const local = readLocal();
    const now = Date.now();
    if (now - (Number(local.lastDownloadAt) || 0) < 4000) return;
    local.lastDownloadAt = now;
    writeLocal(local);
    community.downloads += 1;
    community.ready = true;
    paint();
    postCommunity({ op: "download" }).then((data) => {
      applyData(data, true);
      paint();
    }).catch(() => {
      community.downloads = Math.max(0, community.downloads - 1);
      paint();
    });
  };

  qa(".js-download").forEach((btn) => {
    btn.addEventListener("click", () => {
      const original = btn.dataset.label;
      recordDownload();
      if (!original) return;
      btn.setAttribute("aria-busy", "true");
      btn.textContent = "Preparing…";
      setTimeout(() => {
        btn.textContent = original;
        btn.removeAttribute("aria-busy");
      }, 1200);
    });
  });

  const form = q("#noteForm");
  if (form) {
    const submitBtn = q("#noteSubmit");
    const live = q("#noteLive");
    const nameEl = q("#noteName");
    const noteEl = q("#noteBody");
    const score = q("#noteScore");
    let dirty = false;

    const setErr = (id, msg) => {
      const el = q(id);
      if (!el) return;
      if (msg) {
        el.hidden = false;
        el.textContent = msg;
      } else {
        el.hidden = true;
        el.textContent = "";
      }
    };

    const checkedScore = () => {
      const radio = form.querySelector("input[name=rating]:checked");
      return radio ? Number(radio.value) : 0;
    };

    const paintStars = (upto) => {
      form.querySelectorAll(".score label").forEach((lab) => {
        const input = lab.querySelector("input");
        const icon = lab.querySelector(".star-icon");
        const value = Number(input && input.value);
        const on = value > 0 && value <= upto;
        lab.classList.toggle("is-on", on);
        if (icon) icon.classList.toggle("is-on", on);
      });
    };

    const markDirty = () => { dirty = true; };
    form.addEventListener("input", markDirty);
    form.addEventListener("change", markDirty);
    window.addEventListener("beforeunload", (e) => {
      if (!dirty) return;
      e.preventDefault();
      e.returnValue = "";
    });

    form.querySelectorAll("input[name=rating]").forEach((radio) => {
      radio.addEventListener("change", () => paintStars(checkedScore()));
    });
    if (score) {
      score.addEventListener("pointerover", (e) => {
        const lab = e.target.closest("label");
        if (!lab || !score.contains(lab)) return;
        const value = Number(lab.querySelector("input")?.value);
        if (value) paintStars(value);
      });
      score.addEventListener("pointerleave", () => paintStars(checkedScore()));
    }

    const send = async () => {
      setErr("#errName", "");
      setErr("#errRating", "");
      setErr("#errNote", "");
      if (live) live.textContent = "";

      const name = (nameEl?.value || "").trim();
      const note = (noteEl?.value || "").trim();
      const rating = checkedScore();
      const company = (form.querySelector("[name=company]")?.value || "").trim();
      if (!rating) {
        setErr("#errRating", "Pick a star score.");
        form.querySelector("input[name=rating]")?.focus();
        return;
      }
      if (company) {
        if (live) live.textContent = "Sent.";
        form.reset();
        paintStars(0);
        dirty = false;
        return;
      }

      const original = submitBtn?.dataset.label || "Send";
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.classList.add("is-busy");
        submitBtn.setAttribute("aria-busy", "true");
      }

      try {
        const data = await postCommunity({
          op: "review",
          name,
          note,
          rating,
          at: new Date().toISOString(),
          company: ""
        });
        applyData(data, true);
        form.reset();
        paintStars(0);
        dirty = false;
        if (live) {
          live.textContent = data.mail_ok === false
            ? "Score saved. Email is not set on Render — add RESEND_API_KEY."
            : (note ? "Note sent." : "Score sent.");
        }
        paint();
      } catch {
        if (live) live.textContent = "Could not send.";
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.classList.remove("is-busy");
          submitBtn.removeAttribute("aria-busy");
          submitBtn.textContent = original;
        }
      }
    };

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      send();
    });
    noteEl?.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        send();
      }
    });
  }

  hydrateFromCache();
  paint();
  fetch(COMMUNITY_API)
    .then((res) => (res.ok ? res.json() : Promise.reject()))
    .then((data) => { applyData(data, true); paint(); })
    .catch(() => { paint(); });
})();
