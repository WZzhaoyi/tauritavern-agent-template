import config from './package-config.js';

const ROOT_ID = `tt-interaction-${config.projectId}`;
const TERMINAL_EVENTS = new Set(['run_completed', 'run_failed', 'run_cancelled', 'run_partial_success']);
const PROGRESS_LABELS = {
  run_created: '准备回合',
  profile_resolved: '载入配置',
  workspace_initialized: '载入状态',
  context_assembled: '读取角色卡与世界书',
  model_request_created: '理解玩家行动',
  tool_call_requested: '处理剧情与状态',
  workspace_file_written: '更新状态',
  workspace_patch_applied: '校验状态',
  chat_commit_completed: '提交剧情',
  persistent_changes_committed: '保存进度',
  run_completed: '回合完成',
  run_failed: '回合失败',
  run_cancelled: '已取消',
  run_partial_success: '剧情已提交，但状态收尾失败'
};

const runtime = {
  opened: false,
  busy: false,
  runId: null,
  unsubscribe: null,
  selectedTarget: null,
  baseActions: [],
  regions: [],
  state: null,
  lastActionRecord: null,
  pendingActionLabel: null,
  runChatToken: null,
  runStore: null,
  runCommitted: false,
  runStartedAt: null,
  progressTimer: null,
  statusMessage: '尚未载入',
  statusTone: 'idle'
};

function ttApi() {
  return window.__TAURITAVERN__?.api ?? null;
}

function stContext() {
  return window.SillyTavern?.getContext?.() ?? null;
}

function currentChatToken() {
  const context = stContext();
  return context?.chatId ?? context?.getCurrentChatId?.() ?? null;
}

function parseJson(text, source) {
  try {
    return JSON.parse(text) ?? {};
  } catch (error) {
    throw new Error(`${source} 不是有效 JSON：${error.message}`);
  }
}

function formatRunFailure(event) {
  const detail = event?.payload?.error?.message ?? event?.payload?.message ?? '';
  const code = event?.payload?.code ?? event?.code ?? '';
  const raw = `${code} ${detail}`;
  if (/upstream request failed|error from provider|network error|fetch failed/i.test(raw)) {
    return 'LLM API 上游连接失败；请更换 API 或工具调用稳定的模型后重试';
  }
  if (/model\.tool_call_required|must use agent tools|workspace_finish/i.test(raw)) {
    return '模型未在 Agent 回合预算内完成工具流程；请确认已导入快速事务 Skills，或更换工具调用稳定的模型';
  }
  return detail ? `回合失败：${detail}` : '回合失败；可重试或更换模型';
}

function activeCardMatches() {
  const context = stContext();
  if (!context || context.groupId || context.characterId === undefined) return false;
  const card = context.characters?.[context.characterId];
  const marker = card?.data?.extensions?.tauritavern_interaction;
  return marker?.projectId === config.projectId;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function getUi() {
  const root = document.getElementById(ROOT_ID);
  return {
    root,
    launcher: root?.querySelector('[data-role="launcher"]'),
    panel: root?.querySelector('[data-role="panel"]'),
    status: root?.querySelector('[data-role="status"]'),
    summary: root?.querySelector('[data-role="summary"]'),
    map: root?.querySelector('[data-role="map"]'),
    targets: root?.querySelector('[data-role="targets"]'),
    actions: root?.querySelector('[data-role="actions"]'),
    lore: root?.querySelector('[data-role="lore"]'),
    cancel: root?.querySelector('[data-role="cancel"]'),
    retry: root?.querySelector('[data-role="retry"]')
  };
}

function setStatus(message, tone = 'idle') {
  runtime.statusMessage = message;
  runtime.statusTone = tone;
  renderStatus();
}

function renderStatus() {
  const { status } = getUi();
  if (!status) return;
  const elapsed = runtime.busy && runtime.runStartedAt
    ? ` · ${Math.max(0, Math.floor((Date.now() - runtime.runStartedAt) / 1000))}s`
    : '';
  const action = runtime.busy && runtime.pendingActionLabel
    ? `${runtime.pendingActionLabel} · `
    : '';
  status.textContent = `${action}${runtime.statusMessage}${elapsed}`;
  status.dataset.tone = runtime.statusTone;
}

function startProgressTimer() {
  clearInterval(runtime.progressTimer);
  runtime.progressTimer = window.setInterval(renderStatus, 1000);
}

function stopProgressTimer() {
  clearInterval(runtime.progressTimer);
  runtime.progressTimer = null;
}

function setBusy(busy) {
  runtime.busy = busy;
  const { root, cancel, launcher } = getUi();
  root?.toggleAttribute('data-busy', busy);
  launcher?.toggleAttribute('data-busy', busy);
  root?.querySelectorAll('[data-action-id]').forEach(button => {
    button.disabled = busy;
  });
  if (cancel) cancel.hidden = !busy;
  if (busy) startProgressTimer();
  else stopProgressTimer();
  renderStatus();
}

function createUi() {
  if (document.getElementById(ROOT_ID)) return;

  const root = element('div', 'tt-interaction-root');
  root.id = ROOT_ID;

  const launcher = element('button', 'tt-interaction-launcher', '地图与行动');
  launcher.type = 'button';
  launcher.dataset.role = 'launcher';
  launcher.dataset.ttMobileSurface = 'free-window';
  launcher.setAttribute('aria-label', '打开地图与行动');
  launcher.setAttribute('aria-expanded', 'false');

  const backdrop = element('div', 'tt-interaction-backdrop');
  backdrop.dataset.role = 'backdrop';
  backdrop.dataset.ttMobileSurface = 'backdrop';

  const panel = element('section', 'tt-interaction-panel');
  panel.dataset.role = 'panel';
  panel.dataset.ttMobileSurface = 'fullscreen-window';
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-modal', 'true');
  panel.setAttribute('aria-label', '地图与行动');

  const header = element('header', 'tt-interaction-header');
  const brand = element('div', 'tt-interaction-brand');
  brand.append(
    element('span', 'tt-interaction-kicker', '暂停式回合'),
    element('div', 'tt-interaction-title', config.projectName || '地图与行动')
  );
  const controls = element('div', 'tt-interaction-controls');
  const retry = element('button', '', '重试回合');
  retry.type = 'button';
  retry.dataset.role = 'retry';
  retry.hidden = true;
  const cancel = element('button', '', '取消');
  cancel.type = 'button';
  cancel.dataset.role = 'cancel';
  cancel.hidden = true;
  const close = element('button', '', '返回聊天');
  close.type = 'button';
  close.dataset.role = 'close';
  controls.append(retry, cancel, close);
  header.append(brand, controls);

  const status = element('div', 'tt-interaction-status', '尚未载入');
  status.dataset.role = 'status';
  status.setAttribute('aria-live', 'polite');
  const summary = element('div', 'tt-interaction-summary');
  summary.dataset.role = 'summary';
  const map = element('div', 'tt-interaction-map');
  map.dataset.role = 'map';

  const targetSection = element('section', 'tt-interaction-section tt-interaction-target-section');
  targetSection.append(element('h3', '', '目标'));
  const targets = element('div', 'tt-interaction-targets');
  targets.dataset.role = 'targets';
  targetSection.append(targets);

  const actionSection = element('section', 'tt-interaction-section tt-interaction-action-section');
  actionSection.append(element('h3', '', '行动'));
  const actions = element('div', 'tt-interaction-actions');
  actions.dataset.role = 'actions';
  actionSection.append(actions);

  const loreSection = element('section', 'tt-interaction-section tt-interaction-lore-section');
  loreSection.append(element('h3', '', '本轮设定'));
  const lore = element('div', 'tt-interaction-lore');
  lore.dataset.role = 'lore';
  loreSection.append(lore);

  const stage = element('main', 'tt-interaction-stage');
  stage.append(summary, map);
  const commandDeck = element('aside', 'tt-interaction-command-deck');
  commandDeck.append(targetSection, actionSection, loreSection);
  const gameLayout = element('div', 'tt-interaction-game-layout');
  gameLayout.append(stage, commandDeck);

  panel.append(header, status, gameLayout);
  root.append(launcher, backdrop, panel);
  document.body.append(root);

  launcher.addEventListener('click', () => togglePanel());
  backdrop.addEventListener('click', () => togglePanel(false));
  close.addEventListener('click', () => togglePanel(false));
  cancel.addEventListener('click', cancelRun);
  retry.addEventListener('click', () => startRun(false));

  refreshVisibility();
}

async function togglePanel(force) {
  if (!activeCardMatches()) return;
  runtime.opened = force ?? !runtime.opened;
  const { root, launcher } = getUi();
  root?.toggleAttribute('data-open', runtime.opened);
  launcher?.setAttribute('aria-expanded', String(runtime.opened));
  if (runtime.opened) await loadInterface();
}

function refreshVisibility() {
  const { root } = getUi();
  if (!root) return;
  const visible = activeCardMatches();
  root.toggleAttribute('data-card-active', visible);
  if (!visible) {
    runtime.opened = false;
    root.removeAttribute('data-open');
  }
}

async function readSkillText(path, optional = false) {
  const skillApi = ttApi()?.skill;
  if (!skillApi?.readFile) {
    throw new Error('当前 TauriTavern 未提供 Skill Host API');
  }
  try {
    const file = await skillApi.readFile({ name: config.skillName, path, maxChars: 80000 });
    return file.content;
  } catch (error) {
    if (optional) return null;
    throw error;
  }
}

async function loadInterface() {
  setStatus('载入交互资源…', 'busy');
  try {
    const [actionsText, regionsText, mapText] = await Promise.all([
      readSkillText('assets/actions.json'),
      readSkillText('assets/regions.json'),
      readSkillText('assets/map.svg', true)
    ]);
    runtime.baseActions = parseJson(actionsText, 'assets/actions.json').actions ?? [];
    runtime.regions = parseJson(regionsText, 'assets/regions.json').regions ?? [];
    renderMap(mapText);
    await loadCachedState();
    renderState();
    await renderLore();
    setStatus('请选择目标与行动', 'ready');
  } catch (error) {
    console.error('[TauriTavern Interaction] load failed', error);
    setStatus(`无法载入：${error.message}`, 'error');
  }
}

function renderMap(svgText) {
  const { map } = getUi();
  if (!map) return;
  map.replaceChildren();
  if (!svgText) {
    map.hidden = true;
    return;
  }

  const purifier = window.SillyTavern?.libs?.DOMPurify;
  if (!purifier?.sanitize) {
    map.hidden = true;
    return;
  }
  const safeSvg = purifier.sanitize(svgText, {
    USE_PROFILES: { svg: true, svgFilters: true },
    ADD_ATTR: ['data-region-id', 'tabindex', 'role', 'aria-label']
  });
  map.innerHTML = safeSvg;
  map.hidden = false;
  map.querySelectorAll('[data-region-id]').forEach(node => {
    const select = () => {
      const id = node.getAttribute('data-region-id');
      const region = runtime.regions.find(item => item.id === id) ?? { id, label: id };
      selectTarget({ type: 'region', ...region });
    };
    node.addEventListener('click', select);
    node.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        select();
      }
    });
  });
}

function currentTargets() {
  const dynamic = Array.isArray(runtime.state?.targets) ? runtime.state.targets : [];
  const regions = runtime.regions.map(region => ({ type: 'region', ...region }));
  const seen = new Set();
  return [...dynamic, ...regions].filter(target => {
    const key = `${target.type ?? 'target'}:${target.id}`;
    if (!target?.id || !target?.label || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function currentActions() {
  const dynamic = runtime.state?.actions;
  return Array.isArray(dynamic) && dynamic.length ? dynamic : runtime.baseActions;
}

function scopeMatches(action) {
  const scope = action.scope ?? 'global';
  const scopes = Array.isArray(scope) ? scope : [scope];
  if (scopes.includes('global')) return true;
  return Boolean(runtime.selectedTarget && scopes.includes(runtime.selectedTarget.type));
}

function renderState() {
  const { summary, targets, actions, map } = getUi();
  if (!summary || !targets || !actions) return;

  const turn = runtime.state?.turn;
  const stateSummary = runtime.state?.summary;
  const location = runtime.state?.location?.label;
  summary.textContent = [
    Number.isFinite(turn) ? `回合 ${turn}` : null,
    location ? `当前位置：${location}` : null,
    stateSummary || null
  ].filter(Boolean).join(' · ') || '选择一个目标，或直接执行全局行动。';

  targets.replaceChildren();
  for (const target of currentTargets()) {
    const button = element('button', 'tt-interaction-target', target.label);
    button.type = 'button';
    button.title = target.description ?? '';
    button.toggleAttribute(
      'data-selected',
      runtime.selectedTarget?.id === target.id && runtime.selectedTarget?.type === target.type
    );
    button.addEventListener('click', () => selectTarget(target));
    targets.append(button);
  }

  actions.replaceChildren();
  const available = currentActions().filter(action => action?.id && action?.label && scopeMatches(action));
  for (const action of available) {
    const button = element('button', 'tt-interaction-action');
    button.type = 'button';
    button.dataset.actionId = action.id;
    button.append(element('strong', '', action.label));
    if (action.description) button.append(element('span', '', action.description));
    button.disabled = runtime.busy || Boolean(action.disabled);
    if (action.disabled_reason) button.title = action.disabled_reason;
    button.addEventListener('click', () => submitAction(action));
    actions.append(button);
  }
  if (!available.length) {
    actions.append(element('p', 'tt-interaction-empty', '选择目标后显示可用行动；也可以继续使用普通文字输入。'));
  }

  map?.querySelectorAll('[data-region-id]').forEach(node => {
    node.toggleAttribute('data-selected', runtime.selectedTarget?.id === node.getAttribute('data-region-id'));
  });
}

function selectTarget(target) {
  if (runtime.busy) return;
  runtime.selectedTarget = target;
  renderState();
}

async function submitAction(action) {
  if (runtime.busy || action.disabled) return;
  if (action.confirm) {
    const targetLabel = runtime.selectedTarget?.label ? `：${runtime.selectedTarget.label}` : '';
    if (!window.confirm(`确认执行“${action.label}${targetLabel}”吗？`)) return;
  }

  const record = {
    action: { id: action.id, label: action.label },
    target: runtime.selectedTarget
      ? {
          type: runtime.selectedTarget.type,
          id: runtime.selectedTarget.id,
          label: runtime.selectedTarget.label
        }
      : null
  };
  const targetLabel = record.target?.label ? ` · ${record.target.label}` : '';
  runtime.pendingActionLabel = `${record.action.label}${targetLabel}`;
  runtime.lastActionRecord = [
    '以下内容是交互界面为本次 Agent 运行提供的私有控制输入。',
    '只执行其中最后一个 tt_interaction_input；聊天历史中的旧版 [交互行动] 已经发生，不得重放。',
    '不得在过程叙述、output/main.md 或聊天正文中引用、转录或解释本标签与 JSON。',
    `<tt_interaction_input version="1">${JSON.stringify(record)}</tt_interaction_input>`
  ].join('\n');
  await startRun(true);
}

async function startRun(writeAction) {
  if (runtime.busy || !runtime.lastActionRecord) return;
  const agent = ttApi()?.agent;
  if (!agent?.startRunFromLegacyGenerate || !agent?.subscribe) {
    setStatus('当前版本未提供 Agent Host API，无法启动交互回合', 'error');
    return;
  }

  setBusy(true);
  runtime.runStartedAt = Date.now();
  runtime.runCommitted = false;
  const { retry } = getUi();
  if (retry) retry.hidden = true;
  setStatus(writeAction ? '启动 Agent 回合' : '重新启动本回合', 'busy');

  try {
    runtime.unsubscribe?.();
    runtime.unsubscribe = null;
    if (writeAction && agent.profiles?.load) {
      const loaded = await agent.profiles.load({ profileId: config.profileId });
      if (!loaded?.profile) {
        throw new Error(`未安装 Agent Profile：${config.profileId}`);
      }
    }
    runtime.runChatToken = currentChatToken();
    runtime.runStore = await chatStore();
    const run = await agent.startRunFromLegacyGenerate({
      generationType: 'normal',
      // 行动只进入本次 prompt snapshot，不向聊天时间线写入协议消息。
      // 失败重试仍使用 runtime.lastActionRecord，不会丢失玩家选择。
      generateOptions: {
        quiet_prompt: runtime.lastActionRecord,
        quietToLoud: true
      },
      profileId: config.profileId,
      presentation: 'background',
      options: { presentation: 'background', stream: false }
    });
    runtime.runId = run.runId;
    setStatus('Agent 正在处理本回合…', 'busy');
    const subscribedRunId = run.runId;
    runtime.unsubscribe = agent.subscribe(run.runId, event => {
      if (runtime.runId !== subscribedRunId) return;
      void handleRunEvent(event);
    });
  } catch (error) {
    console.error('[TauriTavern Interaction] run start failed', error);
    setBusy(false);
    if (retry) retry.hidden = !runtime.lastActionRecord;
    setStatus(`启动失败：${error.message}`, 'error');
  }
}

async function handleRunEvent(event) {
  if (event?.runId && event.runId !== runtime.runId) return;
  if (event.type === 'chat_commit_completed') runtime.runCommitted = true;
  const label = PROGRESS_LABELS[event.type];
  if (label && runtime.runChatToken === currentChatToken()) {
    setStatus(label, event.type === 'run_failed' ? 'error' : 'busy');
  }
  if (!TERMINAL_EVENTS.has(event.type)) return;

  runtime.unsubscribe?.();
  runtime.unsubscribe = null;
  setBusy(false);
  const { retry } = getUi();
  const sameChat = runtime.runChatToken === currentChatToken();

  if (event.type === 'run_completed') {
    await refreshStateFromRun(runtime.runId, sameChat, runtime.runStore);
    if (!runtime.runCommitted) {
      if (retry) retry.hidden = false;
      if (sameChat) {
        setStatus('Agent 已结束，但未通过 workspace.commit 发布剧情；可重试本回合', 'error');
      }
    } else {
      runtime.lastActionRecord = null;
      runtime.pendingActionLabel = null;
      if (retry) retry.hidden = true;
    }
    if (sameChat && runtime.runCommitted) {
      await renderLore();
      setStatus('回合完成；返回聊天阅读剧情，或继续选择行动', 'ready');
    }
  } else if (event.type === 'run_partial_success') {
    runtime.lastActionRecord = null;
    runtime.pendingActionLabel = null;
    if (retry) retry.hidden = true;
    if (sameChat) {
      setStatus('剧情已发布，但状态收尾失败；请返回聊天检查本回合', 'error');
    }
  } else {
    if (!sameChat) runtime.lastActionRecord = null;
    if (retry) retry.hidden = !runtime.lastActionRecord;
    if (sameChat) {
      const message = event.type === 'run_failed'
        ? formatRunFailure(event)
        : PROGRESS_LABELS[event.type];
      setStatus(message, event.type === 'run_failed' ? 'error' : 'idle');
    }
  }
  runtime.runStartedAt = null;
  runtime.runStore = null;
}

async function cancelRun() {
  if (!runtime.runId || !runtime.busy) return;
  try {
    await ttApi()?.agent?.cancel?.(runtime.runId);
    setStatus('正在取消…', 'busy');
  } catch (error) {
    setStatus(`取消失败：${error.message}`, 'error');
  }
}

async function refreshStateFromRun(runId, render, cacheStore) {
  if (!runId) return;
  try {
    const file = await ttApi().agent.readWorkspaceFile({ runId, path: config.stateFile });
    const state = parseJson(file.text, config.stateFile);
    await writeCachedState({ runId, sha256: file.sha256, state }, cacheStore);
    if (render) {
      runtime.state = state;
      renderState();
    }
  } catch (error) {
    console.warn('[TauriTavern Interaction] state refresh skipped', error);
    if (render) renderState();
  }
}

async function chatStore() {
  try {
    return ttApi()?.chat?.current?.handle?.()?.store ?? null;
  } catch {
    return null;
  }
}

async function loadCachedState() {
  const store = await chatStore();
  if (!store?.listKeys || !store?.getJson) return;
  try {
    const keys = await store.listKeys({ namespace: config.cacheNamespace });
    if (!keys.includes('interaction-state')) return;
    const cached = await store.getJson({
      namespace: config.cacheNamespace,
      key: 'interaction-state'
    });
    if (cached?.state) runtime.state = cached.state;
  } catch {
    // Cache access is an optional enhancement and must not block the panel.
  }
}

async function writeCachedState(value, storeOverride = null) {
  const store = storeOverride ?? await chatStore();
  if (!store?.setJson) return;
  try {
    await store.setJson({
      namespace: config.cacheNamespace,
      key: 'interaction-state',
      value
    });
  } catch (error) {
    console.warn('[TauriTavern Interaction] cache write skipped', error);
  }
}

async function renderLore() {
  const { lore } = getUi();
  if (!lore) return;
  lore.replaceChildren();
  const worldInfo = ttApi()?.worldInfo;
  if (!worldInfo?.getLastActivation || !worldInfo?.openEntry) {
    lore.closest('.tt-interaction-section').hidden = true;
    return;
  }
  lore.closest('.tt-interaction-section').hidden = false;
  try {
    const activation = await worldInfo.getLastActivation();
    for (const entry of activation?.entries ?? []) {
      const button = element('button', 'tt-interaction-lore-entry', entry.displayName);
      button.type = 'button';
      button.addEventListener('click', () => worldInfo.openEntry({ world: entry.world, uid: entry.uid }));
      lore.append(button);
    }
    if (!lore.childElementCount) lore.append(element('span', 'tt-interaction-empty', '暂无激活条目'));
  } catch (error) {
    lore.append(element('span', 'tt-interaction-empty', '世界书入口暂不可用'));
  }
}

async function initialize() {
  await (window.__TAURITAVERN__?.ready ?? window.__TAURITAVERN_MAIN_READY__ ?? Promise.resolve());
  createUi();
  const context = stContext();
  if (context?.eventSource && context?.event_types?.CHAT_CHANGED) {
    context.eventSource.on(context.event_types.CHAT_CHANGED, () => {
      runtime.state = null;
      runtime.selectedTarget = null;
      if (!runtime.busy) runtime.lastActionRecord = null;
      refreshVisibility();
    });
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initialize, { once: true });
} else {
  void initialize();
}
