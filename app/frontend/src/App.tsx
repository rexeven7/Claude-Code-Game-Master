import { useEffect, useRef, useState } from "react";

const api = (p: string) => fetch(p).then((r) => r.json());
const post = (p: string, body: any) =>
  fetch(p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => r.json());
const del = (p: string) => fetch(p, { method: "DELETE" }).then((r) => r.json());
const pretty = (s: string) => s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export default function App() {
  const [camps, setCamps] = useState<any[]>([]);
  const [arch, setArch] = useState<any[]>([]);
  const [showArch, setShowArch] = useState(false);
  const [cid, setCid] = useState<string | null>(null);
  const [newOpen, setNewOpen] = useState(false);
  const [confirmDel, setConfirmDel] = useState<any>(null);
  const refresh = () => {
    api("/api/campaigns").then(setCamps);
    api("/api/campaigns?include_archived=true").then((all) => setArch((all || []).filter((c: any) => c.archived)));
  };
  useEffect(() => { refresh(); }, []);
  const setArchived = (id: string, on: boolean) => post(`/api/campaigns/${id}/archive`, { archived: on }).then(refresh);
  const doDelete = (id: string) => del(`/api/campaigns/${id}`).then((r) => {
    if (r && r.detail) setConfirmDel((cd: any) => (cd ? { ...cd, error: r.detail } : cd));
    else { setConfirmDel(null); refresh(); }
  });
  if (cid) return <Campaign cid={cid} onBack={() => { setCid(null); refresh(); }} />;
  return (
    <div className="wrap">
      <header className="hero">
        <h1 className="brand">Mythwright</h1>
        <p className="tagline">Your AI Game Master for any world — Forbidden Lands, D&amp;D, or any book you bring.</p>
      </header>

      <div className="sectionhead"><h3>Campaigns</h3><span className="muted">{camps.length} active</span></div>
      <div className="grid">
        {camps.map((c) => (
          <div key={c.id} className="card camp" onClick={() => setCid(c.id)}>
            <button className="cardx" title="Archive" onClick={(e) => { e.stopPropagation(); setArchived(c.id, true); }}>Archive</button>
            <h3>{c.name}</h3>
            <div className="badges">
              {c.system && <span className="badge">{c.system}</span>}
              {c.is_kit && <span className="badge kit">kit</span>}
            </div>
            <div className="muted">{c.current_character || "no character"} · {c.session_count} session{c.session_count === 1 ? "" : "s"}</div>
            {c.location && <div className="muted loc">{c.location}</div>}
          </div>
        ))}
        <div className="card newcard" onClick={() => setNewOpen(true)}>
          <div className="plus">+</div><div>New Adventure</div>
          <div className="muted">Pick a ruleset &amp; begin</div>
        </div>
      </div>

      {arch.length > 0 && (
        <div className="archsec">
          <button className="linkbtn" onClick={() => setShowArch(!showArch)}>{showArch ? "Hide" : "Show"} archived ({arch.length})</button>
          {showArch && (
            <div className="grid">
              {arch.map((c) => (
                <div key={c.id} className="card camp archived">
                  <h3>{c.name}</h3>
                  <div className="muted">{c.current_character || "no character"} · {c.session_count} sessions</div>
                  <div className="cardbtns">
                    <button className="btn" onClick={() => setArchived(c.id, false)}>Restore</button>
                    <button className="btn danger" onClick={() => setConfirmDel({ id: c.id, name: c.name, is_kit: c.is_kit })}>Delete</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {newOpen && <NewAdventure onClose={() => setNewOpen(false)} onCreated={(id: string) => { setNewOpen(false); refresh(); setCid(id); }} />}

      {confirmDel && (
        <div className="overlay" onClick={() => setConfirmDel(null)}>
          <div className="modal confirm" onClick={(e) => e.stopPropagation()}>
            <h2>Delete campaign?</h2>
            <p>Permanently delete <b>{confirmDel.name}</b>? This cannot be undone.</p>
            {confirmDel.is_kit && <p className="muted">Heads up: this world is also a kit other adventures may build on.</p>}
            {confirmDel.error && <div className="err">{confirmDel.error}</div>}
            <div className="wizbtns">
              <button className="btn" onClick={() => setConfirmDel(null)}>Cancel</button><span className="spacer" />
              <button className="btn danger" onClick={() => doDelete(confirmDel.id)}>Delete permanently</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

type Entry = { role: "player" | "gm" | "tool" | "error"; text?: string; name?: string; result?: any; done?: boolean };

function Campaign({ cid, onBack }: { cid: string; onBack: () => void }) {
  const [d, setD] = useState<any>(null);
  const [gal, setGal] = useState<any>(null);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [tab, setTab] = useState<string | null>(null);
  const [zoom, setZoom] = useState<string | null>(null);
  const [txt, setTxt] = useState("");
  const [diceMode, setDiceMode] = useState<"auto" | "manual">("auto");
  const [pendingRoll, setPendingRoll] = useState<any>(null);
  const [painting, setPainting] = useState(false);
  const [rollState, setRollState] = useState<any>(null);
  const ws = useRef<WebSocket | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  const loadGallery = () => api(`/api/campaigns/${cid}/gallery`).then(setGal);
  useEffect(() => { api(`/api/campaigns/${cid}`).then(setD); loadGallery(); }, [cid]);

  useEffect(() => {
    let closed = false; let sock: WebSocket;
    const connect = () => {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      sock = new WebSocket(`${proto}://${location.host}/ws/${cid}`);
      ws.current = sock;
      sock.onmessage = (e) => {
        let ev: any; try { ev = JSON.parse(e.data); } catch { return; }
        if (ev.type === "history") setEntries(ev.entries || []);
        else if (ev.type === "action") push({ role: "player", text: `${ev.character}: ${ev.text}` });
        else if (ev.type === "token") appendToken(ev.text);
        else if (ev.type === "clean") replaceGm(ev.text);
        else if (ev.type === "tool") push({ role: "tool", name: ev.name, result: ev.result });
        else if (ev.type === "roll_request") { setPendingRoll(ev); setRollState(null); }
        else if (ev.type === "roll_state") setRollState(ev);
        else if (ev.type === "status") setPainting(true);
        else if (ev.type === "error") { push({ role: "error", text: ev.text }); setPainting(false); }
        else if (ev.type === "done") { finishGm(); setPendingRoll(null); setRollState(null); setPainting(false); loadGallery(); api(`/api/campaigns/${cid}`).then(setD); }
      };
      sock.onclose = () => { if (!closed) setTimeout(connect, 1500); };
    };
    connect();
    return () => { closed = true; sock?.close(); };
  }, [cid]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [entries]);

  const push = (e: Entry) => setEntries((l) => [...l, e]);
  const appendToken = (t: string) => setEntries((l) => {
    const last = l[l.length - 1];
    if (last && last.role === "gm" && !last.done) {
      const copy = l.slice(); copy[copy.length - 1] = { ...last, text: (last.text || "") + t }; return copy;
    }
    return [...l, { role: "gm", text: t, done: false }];
  });
  const finishGm = () => setEntries((l) => {
    const last = l[l.length - 1];
    if (last && last.role === "gm") { const copy = l.slice(); copy[copy.length - 1] = { ...last, done: true }; return copy; }
    return l;
  });
  const replaceGm = (text: string) => setEntries((l) => {
    for (let i = l.length - 1; i >= 0; i--) if (l[i].role === "gm") { const c = l.slice(); c[i] = { ...c[i], text, done: true }; return c; }
    return l;
  });
  const sendText = (t: string) => { if (t.trim()) ws.current?.send(JSON.stringify({ action: t, character: d?.character?.name || "Player", dice_mode: diceMode })); };
  const send = () => { if (txt.trim()) { ws.current?.send(JSON.stringify({ action: txt, character: d?.character?.name || "Player", dice_mode: diceMode })); setTxt(""); } };
  const sendDice = (m: any) => ws.current?.send(JSON.stringify(m));
  const illustrateNow = () => { if (!painting) { setPainting(true); ws.current?.send(JSON.stringify({ illustrate: true })); } };

  if (!d) return <p className="wrap">Loading…</p>;
  const imgUrl = (path: string) => `/api/campaigns/${cid}/image?path=${encodeURIComponent(path)}`;
  const latest = gal?.scenes?.length ? gal.scenes[gal.scenes.length - 1] : null;

  return (
    <div className={"wrap play-view" + (tab ? " with-drawer" : "")}>
      <div className="topbar">
        <button className="btn" onClick={onBack}>← Dashboard</button>
        <b>{d.overview?.campaign_name}</b>
        <span className="muted">{d.overview?.time_of_day} · {d.overview?.player_position?.current_location}</span>
        <span className="spacer" />
        <button className="btn" onClick={() => setTab(tab === "character" ? null : "character")}>Character</button>
        <button className="btn" onClick={() => setTab(tab === "dice" ? null : "dice")}>Dice</button>
        <button className="btn" onClick={() => setTab(tab === "maps" ? null : "maps")}>Maps</button>
        <button className="btn" onClick={() => setTab(tab === "tools" ? null : "tools")}>Tools</button>
      </div>

      <div className="play">
        {latest && <img className="scene-img" src={imgUrl(latest.path)} alt={latest.label} onClick={() => setZoom(latest.path)} />}
        {painting && <div className="paint-status">🖼 painting a scene… this can take 30–60s</div>}
        <div className="transcript">
          {entries.length === 0 && <p className="muted">Type an action below to begin. The GM will narrate here.</p>}
          {entries.map((e, i) => <TranscriptEntry key={i} e={e} onChoose={sendText} />)}
          <div ref={endRef} />
        </div>
        {pendingRoll && <DiceWidget pending={pendingRoll} state={rollState} send={sendDice} />}
        <div className="actionbar">
          <button className="btn" title="toggle dice mode" onClick={() => setDiceMode(diceMode === "auto" ? "manual" : "auto")}>
            {diceMode === "auto" ? "🎲 auto" : "✋ manual"}
          </button>
          <input value={txt} onChange={(e) => setTxt(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()}
                 placeholder="Describe your action…" />
          <button className="btn" onClick={send}>Send</button>
          <button className="btn" title="paint the current scene" onClick={illustrateNow} disabled={painting}>{painting ? "🖼 painting…" : "🖼 Illustrate"}</button>
        </div>
      </div>

      {tab && (
        <>
          <div className="drawer open">
            <div className="drawer-tabs">
              {["character", "party", "dice", "maps", "tools"].map((t) => (
                <button key={t} className={"tab" + (tab === t ? " active" : "")} onClick={() => setTab(t)}>{pretty(t)}</button>
              ))}
              <span className="spacer" />
              <button className="tab" onClick={() => setTab(null)}>✕</button>
            </div>
            {tab === "character" && d.character && <CharacterSheet ch={d.character} />}
            {tab === "party" && <Party party={d.party} />}
            {tab === "dice" && <DiceTray />}
            {tab === "maps" && <Gallery gal={gal} imgUrl={imgUrl} onZoom={setZoom} />}
            {tab === "tools" && <ToolsPanel cid={cid} onSend={(t: string) => { sendText(t); setTab(null); }} />}
          </div>
        </>
      )}

      {zoom && <div className="overlay" onClick={() => setZoom(null)}><img src={imgUrl(zoom)} alt="" /></div>}
    </div>
  );
}

function renderInline(str: string) {
  return str.split(/\*\*/).map((part, i) => (i % 2 ? <strong key={i}>{part}</strong> : <span key={i}>{part}</span>));
}

function TranscriptEntry({ e, onChoose }: { e: Entry; onChoose: (t: string) => void }) {
  if (e.role === "player") return <div className="player-line">» {e.text}</div>;
  if (e.role === "error") return <div className="err">{e.text}</div>;
  if (e.role === "tool") {
    const r = e.result || {};
    if (e.name === "roll_dice") {
      return (
        <div>
          <span className="chip">🎲 {r.successes ?? 0} success{r.successes === 1 ? "" : "es"}{r.pushed ? " · pushed" : ""}{r.attribute_banes ? ` · ▼${r.attribute_banes} attr` : ""}</span>
          {r.faces && <DiceRow faces={r.faces} />}
        </div>
      );
    }
    let label: any = e.name;
    if (e.name === "move_to") label = `→ moved to ${r.location || "?"}`;
    else if (e.name === "illustrate") label = r.error ? `🖼 image failed (${r.error})` : "🖼 painted a scene";
    else if (e.name === "lookup") label = "📖 consulted the books";
    else if (e.name === "update_character") label = "✎ character updated";
    else if (e.name === "record_event") label = "✎ noted";
    return <div><span className="chip">{label}</span></div>;
  }
  const lines = (e.text || "").split("\n");
  const opts: string[] = []; const prose: string[] = [];
  for (const ln of lines) {
    const m = ln.match(/^\s*\*{0,2}\s*\d+[.)]\s*(.+?)\*{0,2}\s*$/);
    if (m && m[1]) opts.push(m[1].replace(/\*\*/g, "").trim()); else prose.push(ln);
  }
  return (
    <div className="gm-text">
      {prose.join("\n").split(/\n\n+/).map((para) => para.trim()).filter(Boolean).map((para, i) => <p key={i}>{renderInline(para)}</p>)}
      {opts.length > 0 && (
        <div className="choices">
          {opts.map((o, i) => <button key={i} className="choice" onClick={() => onChoose(o)}>{i + 1}. {o}</button>)}
        </div>
      )}
    </div>
  );
}

function CharacterSheet({ ch }: { ch: any }) {
  const a = ch.attributes || {}, cur = ch.current_attributes || a;
  const wp = ch.willpower || {}, skills = ch.skills || {}, va = ch.visual_appearance || {};
  return (
    <div>
      <h3>{ch.name} <span className="muted">· {ch.race} {ch.class} · L{ch.level}</span></h3>
      <div className="attrs">
        {["strength", "agility", "wits", "empathy"].map((k) => (
          <span key={k} className="attr"><b>{k.slice(0, 3).toUpperCase()}</b> {cur[k] ?? a[k]}/{a[k]}</span>
        ))}
        {wp.max != null && <span className="attr"><b>WP</b> {wp.current}/{wp.max}</span>}
        {ch.gold != null && <span className="attr"><b>Gold</b> {ch.gold}</span>}
      </div>
      {ch.conditions?.length > 0 && <div className="muted">Conditions: {ch.conditions.join(", ")}</div>}
      <h4 style={{ margin: ".7rem 0 .2rem" }}>Skills</h4>
      <div className="sheet">
        {Object.entries(skills).map(([k, v]: any) => (
          <div key={k} className={"skill" + (v ? "" : " zero")}><span>{pretty(k)}</span><span>{v}</span></div>
        ))}
      </div>
      {ch.features?.length > 0 && <><h4 style={{ margin: ".7rem 0 .2rem" }}>Talents</h4>
        <div>{ch.features.map((f: string, i: number) => <span key={i} className="tag">{f}</span>)}</div></>}
      {(ch.inventory?.length > 0 || ch.equipment?.length > 0) && <><h4 style={{ margin: ".7rem 0 .2rem" }}>Gear</h4>
        <div>{[...(ch.inventory || []), ...(ch.equipment || [])].map((it: string, i: number) => <span key={i} className="tag">{it}</span>)}</div></>}
      {ch.pride && <p><b>Pride:</b> {ch.pride}</p>}
      {ch.dark_secret && <p><b>Dark Secret:</b> {ch.dark_secret}</p>}
      {ch.background && <p className="muted"><b>Background:</b> {ch.background}</p>}
      {Object.keys(va).length > 0 && <details><summary>Appearance</summary>
        <div className="muted">{Object.entries(va).map(([k, v]: any) => `${pretty(k)}: ${v}`).join(" · ")}</div></details>}
    </div>
  );
}

function Party({ party }: { party: any }) {
  const names = Object.keys(party || {});
  if (names.length === 0) return <p className="muted">No party members yet. (Promote companions with gm-npc.)</p>;
  return <div>{names.map((n) => {
    const s = party[n].character_sheet || {}, a = s.attributes || {};
    return <div key={n} className="bar">{n} — {s.race} {s.class}
      {a.strength != null && ` · STR ${a.strength} AGI ${a.agility} WITS ${a.wits} EMP ${a.empathy}`}</div>;
  })}</div>;
}

function DiceTray() {
  const [mode, setMode] = useState<"auto" | "manual">("auto");
  const [p, setP] = useState({ base: 4, skill: 2, gear: 0 });
  const [faces, setFaces] = useState({ base: "", skill: "", gear: "" });
  const [res, setRes] = useState<any>(null);
  const parse = (s: string) => s.split(/[ ,]+/).filter(Boolean).map(Number);
  const rollAuto = (push: boolean) => api(`/api/dice/yze?base=${p.base}&skill=${p.skill}&gear=${p.gear}&push=${push}`).then(setRes);
  const score = (pushed: boolean) => fetch("/api/dice/score", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ base: parse(faces.base), skill: parse(faces.skill), gear: parse(faces.gear), pushed }) }).then((r) => r.json()).then(setRes);
  return (
    <div>
      <h3>Dice <span className="muted">· {mode}</span></h3>
      <button className="btn" onClick={() => { setMode(mode === "auto" ? "manual" : "auto"); setRes(null); }}>switch to {mode === "auto" ? "manual" : "auto"}</button>
      <div style={{ marginTop: ".6rem" }}>
        {mode === "auto" ? (<>
          {(["base", "skill", "gear"] as const).map((k) => (
            <label key={k} style={{ marginRight: ".6rem" }}>{k} <input type="number" value={(p as any)[k]} onChange={(e) => setP({ ...p, [k]: +e.target.value })} /></label>))}
          <div style={{ marginTop: ".5rem" }}>
            <button className="btn" onClick={() => rollAuto(false)}>Roll</button>{" "}
            <button className="btn" onClick={() => rollAuto(true)}>Roll + Push</button></div>
        </>) : (<>
          <p className="muted">Roll your real dice, type the faces (e.g. "6 3 1"):</p>
          {(["base", "skill", "gear"] as const).map((k) => (
            <label key={k} style={{ marginRight: ".6rem" }}>{k} <input style={{ width: 90 }} value={(faces as any)[k]} onChange={(e) => setFaces({ ...faces, [k]: e.target.value })} /></label>))}
          <div style={{ marginTop: ".5rem" }}>
            <button className="btn" onClick={() => score(false)}>Score</button>{" "}
            <button className="btn" onClick={() => score(true)}>Score (pushed)</button></div>
        </>)}
      </div>
      {res && <div className="bar">{res.successes} success{res.successes === 1 ? "" : "es"}
        {res.pushed ? ` · banes ▼${res.attribute_banes} · +${res.willpower} WP${res.gear_banes ? ` · gear −${res.gear_banes}` : ""}` : (res.can_push ? " · (can push)" : "")}</div>}
    </div>
  );
}

function Gallery({ gal, imgUrl, onZoom }: any) {
  if (!gal) return null;
  const Section = ({ title, items }: any) => items?.length > 0 && (
    <><h4 style={{ margin: ".6rem 0 .3rem" }}>{title}</h4>
      <div className="row">{items.map((it: any) => (
        <img key={it.path} className="thumb" alt={it.label} title={it.label} src={imgUrl(it.path)} onClick={() => onZoom(it.path)} />))}</div></>);
  return (<div>
    <h3>Gallery</h3>
    <Section title="Scenes so far" items={gal.scenes} />
    <Section title="Maps (visited)" items={gal.maps} />
    {!gal.scenes?.length && !gal.maps?.length && <p className="muted">No images yet.</p>}
  </div>);
}

function Die({ f, kind }: { f: number; kind: string }) {
  const bane = f === 1 && kind !== "skill";
  const cls = "die " + kind + (f === 6 ? " success" : bane ? " bane" : " blank");
  return <span className={cls} title={`${kind} die: ${f}`}>{f === 6 ? "⚔" : bane ? "💀" : f}</span>;
}
function DiceRow({ faces }: { faces: any }) {
  const grp = (label: string, arr: number[], kind: string) =>
    arr && arr.length > 0 ? (
      <div className="dgrp"><span className="dlab">{label}</span>{arr.map((f, i) => <Die key={i} f={f} kind={kind} />)}</div>
    ) : null;
  return <div className="dicerow">{grp("Base", faces?.base, "base")}{grp("Skill", faces?.skill, "skill")}{grp("Gear", faces?.gear, "gear")}</div>;
}
function DicePreview({ pool }: { pool: any }) {
  const slot = (n: number, kind: string) => Array.from({ length: n || 0 }).map((_, i) => <span key={kind + i} className={"die " + kind + " blank"} />);
  return (
    <div className="dicerow">
      <div className="dgrp"><span className="dlab">Base</span>{slot(pool.base, "base")}</div>
      {pool.skill > 0 && <div className="dgrp"><span className="dlab">Skill</span>{slot(pool.skill, "skill")}</div>}
      {pool.gear > 0 && <div className="dgrp"><span className="dlab">Gear</span>{slot(pool.gear, "gear")}</div>}
    </div>
  );
}
function DiceWidget({ pending, state, send }: { pending: any; state: any; send: (m: any) => void }) {
  const pool = pending.pool || {};
  const mode = pending.mode || "auto";
  const total = (pool.base || 0) + (pool.skill || 0) + (pool.gear || 0);
  const label = pending.label || "a test";
  const attr = pending.attribute || "";
  const comp = `${attr ? attr + " " : ""}${pool.base} + skill ${pool.skill} + gear ${pool.gear} = ${total} dice`;
  const [f, setF] = useState({ base: "", skill: "", gear: "" });
  const [pushing, setPushing] = useState(false);
  const parse = (v: string) => v.split(/[ ,]+/).filter(Boolean).map(Number);
  if (state) {
    return (
      <div className="card dice">
        <b>🎲 {label}</b> <span className="muted">{comp}{state.pushed ? " · pushed" : ""}</span>
        <DiceRow faces={state.faces} />
        <div className="diceres">
          {state.success
            ? <span className="ok">{state.successes} success{state.successes === 1 ? "" : "es"} ⚔</span>
            : <span className="fail">Failure — 0 successes ✗</span>}
          {state.pushed && state.attribute_banes > 0 && <span className="bane"> · ▼{state.attribute_banes} attribute 💀 · +{state.willpower} WP</span>}
          {state.pushed && state.gear_banes > 0 && <span className="bane"> · gear damaged ×{state.gear_banes}</span>}
        </div>
        {pushing && mode === "manual" ? (
          <div>
            <div className="muted">Reroll your non-6 / non-1 dice and enter ALL faces again:</div>
            {(["base", "skill", "gear"] as const).map((k) => (
              <label key={k} style={{ marginRight: ".6rem" }}>{k} <input style={{ width: 90 }} value={(f as any)[k]}
                onChange={(e) => setF({ ...f, [k]: e.target.value })} placeholder={`${pool[k]} dice`} /></label>
            ))}
            <button className="btn" onClick={() => { send({ dice: "score", base: parse(f.base), skill: parse(f.skill), gear: parse(f.gear), pushed: true }); setPushing(false); }}>Submit pushed faces</button>
          </div>
        ) : (
          <div className="dicebtns">
            {state.can_push && mode === "auto" && <button className="btn" onClick={() => send({ dice: "push" })}>Push (reroll)</button>}
            {state.can_push && mode === "manual" && <button className="btn" onClick={() => setPushing(true)}>Push (reroll)</button>}
            <button className="btn" onClick={() => send({ dice: "keep" })}>Keep &amp; continue</button>
          </div>
        )}
      </div>
    );
  }
  return (
    <div className="card dice">
      <b>🎲 The GM calls for a roll — {label}</b>
      <div className="muted">{comp}{pool.push ? " · push allowed" : ""}</div>
      <DicePreview pool={pool} />
      {mode === "auto" ? (
        <button className="btn" onClick={() => send({ dice: "roll" })}>Roll {total} dice</button>
      ) : (
        <div>
          <div className="muted">Roll your real dice and enter the faces:</div>
          {(["base", "skill", "gear"] as const).map((k) => (
            <label key={k} style={{ marginRight: ".6rem" }}>{k} <input style={{ width: 90 }} value={(f as any)[k]}
              onChange={(e) => setF({ ...f, [k]: e.target.value })} placeholder={`${pool[k]} dice`} /></label>
          ))}
          <button className="btn" onClick={() => send({ dice: "score", base: parse(f.base), skill: parse(f.skill), gear: parse(f.gear), pushed: false })}>Submit faces</button>
        </div>
      )}
    </div>
  );
}


function NewAdventure({ onClose, onCreated }: { onClose: () => void; onCreated: (id: string) => void }) {
  const [opts, setOpts] = useState<any>(null);
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [advName, setAdvName] = useState("");
  const [kits, setKits] = useState<any[]>([]);
  const [kit, setKit] = useState<string>("");
  const [gen, setGen] = useState<any>({ name: "", identity: "original", concept: "" });
  useEffect(() => { api("/api/kits").then(setKits); }, []);
  const kitObj = kits.find((k: any) => k.id === kit);
  const create = () => {
    if (!advName.trim()) { setErr("Name your adventure."); setStep(0); return; }
    setBusy(true); setErr("");
    post("/api/campaigns", { name: advName, kit, character: kitObj?.creation === "generic" ? gen : s })
      .then((r) => { if (r?.id) onCreated(r.id); else { setErr(r?.detail || "Could not create."); setBusy(false); } })
      .catch(() => { setErr("Could not create."); setBusy(false); });
  };
  const [s, setS] = useState<any>({ name: "", kin: "Human", profession: "Hunter", sex: "", age: "Adult",
    attributes: { strength: 2, agility: 2, wits: 2, empathy: 2 }, skills: {},
    profession_talent: "", general_talents: [], pride: "", dark_secret: "", background: "", appearance: {} });
  const ATTRS = ["strength", "agility", "wits", "empathy"];
  const p2 = (x: string) => x.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const kinOf = (n: string) => opts?.kins.find((k: any) => k.name === n);
  const profOf = (n: string) => opts?.professions.find((q: any) => q.name === n);
  const legalAttrs = (kin: string, prof: string, age: string) => {
    const pk = profOf(prof)?.key_attribute, kk = kinOf(kin)?.key_attribute;
    const cp = (a: string) => (a === pk && a === kk) ? 6 : (a === pk || a === kk) ? 5 : 4;
    const a: any = { strength: 2, agility: 2, wits: 2, empathy: 2 };
    let rem = opts.ages[age].attribute_points - 8;
    const ord = [...ATTRS].sort((x, y) => cp(y) - cp(x)); let i = 0;
    while (rem > 0 && ATTRS.some((x) => a[x] < cp(x))) { const x = ord[i % 4]; if (a[x] < cp(x)) { a[x]++; rem--; } i++; }
    return a;
  };
  const legalSkills = (prof: string, age: string) => {
    const sk: any = {}; const ps = profOf(prof)?.skills || []; let rem = opts.ages[age].skill_points, i = 0;
    while (rem > 0 && ps.length && ps.some((x: string) => (sk[x] || 0) < 3)) { const x = ps[i % ps.length]; if ((sk[x] || 0) < 3) { sk[x] = (sk[x] || 0) + 1; rem--; } i++; }
    return sk;
  };
  const applyDefaults = (n: any) => {
    n.attributes = legalAttrs(n.kin, n.profession, n.age);
    n.skills = legalSkills(n.profession, n.age);
    n.profession_talent = profOf(n.profession)?.talents?.[0]?.name || "";
    n.general_talents = []; n.pride = profOf(n.profession)?.pride?.[0] || ""; n.dark_secret = profOf(n.profession)?.dark_secret?.[0] || "";
    return n;
  };
  useEffect(() => { if (kit && kitObj?.creation === "fbl") api(`/api/kits/${kit}/options`).then(setOpts); }, [kit]);
  useEffect(() => { if (opts) setS((pp: any) => applyDefaults({ ...pp })); }, [opts]);
  if (!kit) return (
    <div className="overlay" onClick={onClose}>
      <div className="modal wizard" onClick={(e) => e.stopPropagation()}>
        <h2>New Adventure</h2>
        <p className="muted">Choose your ruleset and world. Each kit brings its own rules - combat, skills, magic, and advancement.</p>
        {kits.length === 0 && <p className="muted">Loading kits...</p>}
        <div className="kitlist">
          {kits.map((k: any) => (
            <div key={k.id} className="card kit" onClick={() => { setKit(k.id); setStep(0); setErr(""); }}>
              <b>{k.name}</b> <span className="muted">{k.system}{k.creation === "fbl" ? " - full character builder" : ""}</span>
              {k.description && <p className="muted">{k.description}</p>}
            </div>
          ))}
        </div>
        <p className="muted">Want another world? In Claude Code, run <code>/import &lt;your-book.pdf&gt;</code> and choose a rule system (Forbidden Lands / Year Zero, or D&amp;D / d20). It builds a kit - RAG indexing runs on your own machine - that then appears here to play.</p>
        <div className="wizbtns"><button className="btn" onClick={onClose}>Cancel</button></div>
      </div>
    </div>
  );
  if (kitObj?.creation === "generic") return (
    <div className="overlay" onClick={onClose}>
      <div className="modal wizard" onClick={(e) => e.stopPropagation()}>
        <h2>New Adventure - {kitObj.name}</h2>
        <p className="muted">{kitObj.system}. Sketch your character; the Game Master fleshes out the details in play.</p>
        <label className="fld">Adventure name<input value={advName} onChange={(e) => setAdvName(e.target.value)} placeholder="The Long Road" /></label>
        <label className="fld">Character name<input value={gen.name} onChange={(e) => setGen({ ...gen, name: e.target.value })} placeholder="(blank = Wanderer)" /></label>
        <label className="fld">Who are you in this world?
          <select value={gen.identity} onChange={(e) => setGen({ ...gen, identity: e.target.value })}>
            <option value="original">An original character</option>
            <option value="canon">A canon figure from the source</option>
            <option value="nameless">Nameless - discover who you are in play</option>
          </select>
        </label>
        <label className="fld">Concept<textarea rows={3} value={gen.concept} onChange={(e) => setGen({ ...gen, concept: e.target.value })} placeholder="A line or two: what you are, what drives you..." /></label>
        {err && <div className="err">{err}</div>}
        <div className="wizbtns">
          <button className="btn" onClick={onClose}>Cancel</button><span className="spacer" />
          <button className="btn" onClick={() => setKit("")}>Ruleset</button>
          <button className="btn" onClick={create} disabled={busy}>{busy ? "Creating..." : "Begin"}</button>
        </div>
      </div>
    </div>
  );
  if (!opts) return (<div className="overlay" onClick={onClose}><div className="modal" onClick={(e) => e.stopPropagation()}>Loading…</div></div>);
  const prof = profOf(s.profession), kin = kinOf(s.kin), age = opts.ages[s.age];
  const cap = (a: string) => { const pk = prof?.key_attribute, kk = kin?.key_attribute; return (a === pk && a === kk) ? 6 : (a === pk || a === kk) ? 5 : 4; };
  const attrUsed = ATTRS.reduce((n, a) => n + (s.attributes[a] || 0), 0);
  const skillUsed = (Object.values(s.skills).reduce((n: any, v: any) => n + (v || 0), 0)) as number;
  const genCap = age.general_talents;
  const up = (patch: any) => setS((pp: any) => ({ ...pp, ...patch }));
  const setKPA = (patch: any) => setS((pp: any) => applyDefaults({ ...pp, ...patch }));
  const setAttr = (a: string, d: number) => setS((pp: any) => ({ ...pp, attributes: { ...pp.attributes, [a]: Math.max(2, Math.min(cap(a), (pp.attributes[a] || 2) + d)) } }));
  const setSkill = (sk: string, d: number) => setS((pp: any) => ({ ...pp, skills: { ...pp.skills, [sk]: Math.max(0, Math.min(3, (pp.skills[sk] || 0) + d)) } }));
  const setApp = (k: string, v: string) => setS((pp: any) => ({ ...pp, appearance: { ...pp.appearance, [k]: v } }));
  const toggleGen = (t: string) => setS((pp: any) => { const has = pp.general_talents.includes(t); let g = has ? pp.general_talents.filter((x: string) => x !== t) : [...pp.general_talents, t]; if (g.length > genCap) g = g.slice(g.length - genCap); return { ...pp, general_talents: g }; });
  const steps = ["Identity", "Attributes", "Skills", "Talents", "Pride & Secret", "Look", "Review"];
  const customPride = !(prof?.pride || []).includes(s.pride);
  const customDark = !(prof?.dark_secret || []).includes(s.dark_secret);
  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal wizard" onClick={(e) => e.stopPropagation()}>
        <h2>New Adventure</h2>
        <div className="steps">{steps.map((t, i) => <span key={i} className={"stp" + (i === step ? " on" : i < step ? " done" : "")} onClick={() => setStep(i)}>{i + 1}. {t}</span>)}</div>
        {step === 0 && (<div>
          <p className="muted">You begin in the wilds of Hex I20 — Weatherstone is only a rumor until you travel and hear its legend.</p>
          <label className="fld">Adventure name<input value={advName} onChange={(e) => setAdvName(e.target.value)} placeholder="The Long Road North" /></label>
          <label className="fld">Character name<input value={s.name} onChange={(e) => up({ name: e.target.value })} placeholder="(blank = random)" /></label>
          <div className="frow">
            <label className="fld">Kin<select value={s.kin} onChange={(e) => setKPA({ kin: e.target.value })}>{opts.kins.map((k: any) => <option key={k.name}>{k.name}</option>)}</select></label>
            <label className="fld">Profession<select value={s.profession} onChange={(e) => setKPA({ profession: e.target.value })}>{opts.professions.map((q: any) => <option key={q.name}>{q.name}</option>)}</select></label>
            <label className="fld">Age<select value={s.age} onChange={(e) => setKPA({ age: e.target.value })}>{Object.keys(opts.ages).map((a) => <option key={a}>{a}</option>)}</select></label>
            <label className="fld">Sex<select value={s.sex} onChange={(e) => up({ sex: e.target.value })}><option value="">(random)</option><option value="male">male</option><option value="female">female</option></select></label>
          </div>
          {kin && <p className="muted"><b>Kin talent:</b> {kin.talent.name} — {kin.talent.desc}</p>}
          {prof && <p className="muted"><b>{prof.name}:</b> key {p2(prof.key_attribute)}; skills {prof.skills.map(p2).join(", ")}.</p>}
        </div>)}
        {step === 1 && (<div>
          <p className="muted">Distribute attribute points — <b>{attrUsed}/{age.attribute_points}</b> used. Each 2–4; a ★ key attribute up to {Math.max(...ATTRS.map(cap))}.</p>
          {ATTRS.map((a) => (<div key={a} className="prow"><span className="plab">{p2(a)} {(a === prof?.key_attribute || a === kin?.key_attribute) ? "★" : ""}</span>
            <button className="btn" onClick={() => setAttr(a, -1)}>−</button><span className="pval">{s.attributes[a]}</span>
            <button className="btn" onClick={() => setAttr(a, 1)} disabled={attrUsed >= age.attribute_points || s.attributes[a] >= cap(a)}>+</button>
            <span className="muted">max {cap(a)}</span></div>))}
        </div>)}
        {step === 2 && (<div>
          <p className="muted">Distribute skill points among your profession skills — <b>{skillUsed}/{age.skill_points}</b> used. Max 3 each.</p>
          {(prof?.skills || []).map((sk: string) => (<div key={sk} className="prow"><span className="plab">{p2(sk)}</span>
            <button className="btn" onClick={() => setSkill(sk, -1)}>−</button><span className="pval">{s.skills[sk] || 0}</span>
            <button className="btn" onClick={() => setSkill(sk, 1)} disabled={skillUsed >= age.skill_points || (s.skills[sk] || 0) >= 3}>+</button></div>))}
        </div>)}
        {step === 3 && (<div>
          <p className="muted"><b>Kin talent (automatic):</b> {kin?.talent.name} — {kin?.talent.desc}</p>
          <h4>Profession talent — choose one</h4>
          {(prof?.talents || []).map((t: any) => (<label key={t.name} className="opt"><input type="radio" name="ptal" checked={s.profession_talent === t.name} onChange={() => up({ profession_talent: t.name })} /> <b>{t.name}</b> — <span className="muted">{t.desc}</span></label>))}
          <h4>General talents — choose {genCap} ({s.general_talents.length}/{genCap})</h4>
          <div className="genwrap">{opts.general_talents.map((g: string) => (<label key={g} className={"gtal" + (s.general_talents.includes(g) ? " on" : "")}><input type="checkbox" checked={s.general_talents.includes(g)} onChange={() => toggleGen(g)} /> {g}</label>))}</div>
        </div>)}
        {step === 4 && (<div>
          <h4>Pride — choose one or write your own</h4>
          {(prof?.pride || []).map((o: string) => (<label key={o} className="opt"><input type="radio" name="pr" checked={s.pride === o} onChange={() => up({ pride: o })} /> {o}</label>))}
          <input className="full" placeholder="…or write your own Pride" value={customPride ? s.pride : ""} onChange={(e) => up({ pride: e.target.value })} />
          <h4>Dark Secret — choose one or write your own</h4>
          {(prof?.dark_secret || []).map((o: string) => (<label key={o} className="opt"><input type="radio" name="ds" checked={s.dark_secret === o} onChange={() => up({ dark_secret: o })} /> {o}</label>))}
          <input className="full" placeholder="…or write your own Dark Secret" value={customDark ? s.dark_secret : ""} onChange={(e) => up({ dark_secret: e.target.value })} />
        </div>)}
        {step === 5 && (<div>
          <p className="muted">How do others see you? (optional — sensible defaults fill in)</p>
          <div className="frow">{["hair", "face", "eyes", "clothing", "demeanor", "size"].map((k) => (<label key={k} className="fld">{p2(k)}<input value={s.appearance[k] || ""} onChange={(e) => setApp(k, e.target.value)} /></label>))}</div>
          <label className="fld">Background<textarea rows={3} value={s.background} onChange={(e) => up({ background: e.target.value })} placeholder="A line or two on where you came from…" /></label>
        </div>)}
        {step === 6 && (<div className="review">
          <h3>{s.name || "(random name)"} — {s.kin} {s.profession} <span className="muted">({s.age})</span></h3>
          <div className="bar">STR {s.attributes.strength} · AGI {s.attributes.agility} · WITS {s.attributes.wits} · EMP {s.attributes.empathy}</div>
          <div className="muted">Skills: {Object.entries(s.skills).filter(([, v]: any) => v).map(([k, v]: any) => p2(k) + " " + v).join(", ") || "(none)"}</div>
          <div className="muted">Talents: {kin?.talent.name}, {s.profession_talent}{s.general_talents.length ? ", " + s.general_talents.join(", ") : ""}</div>
          <p><b>Pride:</b> {s.pride}</p><p><b>Dark Secret:</b> {s.dark_secret}</p>
          {err && <div className="err">{err}</div>}
        </div>)}
        <div className="wizbtns">
          <button className="btn" onClick={onClose}>Cancel</button><span className="spacer" />
          {step > 0 ? <button className="btn" onClick={() => setStep(step - 1)}>Back</button> : <button className="btn" onClick={() => setKit("")}>Ruleset</button>}
          {step < 6 ? <button className="btn" onClick={() => setStep(step + 1)}>Next</button>
                    : <button className="btn" onClick={create} disabled={busy}>{busy ? "Creating…" : "Begin the hunt"}</button>}
        </div>
      </div>
    </div>
  );
}


function ToolsPanel({ cid, onSend }: { cid: string; onSend: (t: string) => void }) {
  const [res, setRes] = useState<any>(null);
  const [busy, setBusy] = useState("");
  const roll = (kind: string, opts: any = {}) => {
    setBusy(kind + (opts.mode || "") + (opts.named ? "-named" : "")); setRes(null);
    post(`/api/campaigns/${cid}/generate`, { kind, ...opts }).then((r) => { setRes(r); setBusy(""); }).catch(() => setBusy(""));
  };
  return (
    <div>
      <h3>Tools <span className="muted">&middot; rolled from your books</span></h3>
      <p className="muted">Real Forbidden Lands tables (GM&rsquo;s Guide + Book of Beasts), grounded with passages from your own PDFs.</p>
      <div className="toolgrid">
        <button className="btn" onClick={() => roll("legend")}>Legend / rumor</button>
        <button className="btn" onClick={() => roll("monster", { mode: "pick" })}>Random monster</button>
        <button className="btn" onClick={() => roll("monster", { mode: "build" })}>Build a monster</button>
        <button className="btn" onClick={() => roll("npc")}>NPC</button>
        <button className="btn" onClick={() => roll("site")}>Adventure site</button>
        <button className="btn" onClick={() => roll("site", { named: true })}>Named site</button>
      </div>
      {busy && <p className="muted">rolling {busy}&hellip;</p>}
      {res && <ToolResult res={res} onSend={onSend} />}
    </div>
  );
}

function ToolResult({ res, onSend }: { res: any; onSend: (t: string) => void }) {
  if (res.error) return <div className="err">{res.error}</div>;
  const b = res.block;
  const title = res.title || res.name || (res.kind === "npc" ? `${res.kin} ${res.profession}` : res.type ? `A ${res.type}` : "Result");
  return (
    <div className="toolres">
      <h4>{title}</h4>
      {res.source && <div className="muted">source: {res.source}</div>}
      {res.roll && <div className="muted">D66 &rarr; {res.roll}</div>}
      {res.category && <div className="muted">legend type: {res.category}</div>}
      {b && (
        <div className="bar">
          {b.attributes && <div>STR {b.attributes.strength} &middot; AGI {b.attributes.agility} &middot; WITS {b.attributes.wits} &middot; EMP {b.attributes.empathy} &middot; Armor {b.armor}</div>}
          {b.ability && b.ability.length > 0 && <div>Ability: {b.ability.join("; ")}</div>}
          {b.attacks && b.attacks.length > 0 && <div>Attacks: {b.attacks.join(" | ")}</div>}
          {b.strength && b.strength.length > 0 && <div>Strength: {b.strength.join("; ")}</div>}
          {b.weakness && <div>Weakness: {b.weakness}</div>}
          {b.skills && <div className="muted">Skills: {Object.entries(b.skills).map(([k, v]: any) => `${k} ${v}`).join(", ")}</div>}
        </div>
      )}
      {res.passages && res.passages.length > 0 && (
        <details open><summary>From your books</summary>
          {res.passages.map((pp: string, i: number) => <p key={i} className="muted">{pp}</p>)}
        </details>
      )}
      {res.passages && res.passages.length === 0 && res.grounded === false && (
        <p className="muted">(Book passages load when the RAG index is reachable on your machine.)</p>
      )}
      <button className="btn" onClick={() => onSend(res.text)}>Send to scene</button>
    </div>
  );
}
