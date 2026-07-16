import config from './package-config.js';

const ROOT_ID = `tt-interaction-${config.projectId}`;
const TERMINAL_EVENTS = new Set(['run_completed', 'run_failed', 'run_cancelled']);
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
  run_cancelled: '已取消'
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
  runChatToken: null,
  runStore: null
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

function parseYaml(text) {
  const yaml = window.SillyTavern?.libs?.yaml;
  if (!yaml?.parse) {
    throw new Error('当前 SillyTavern 上下文未提供 YAML 解析器');
  }
  return yaml.parse(text) ?? {};
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
  const { status } = getUi();
  if (!status) return;
  status.textContent = message;
  status.dataset.tone = tone;
}

function setBusy(busy) {
  runtime.busy = busy;
  const { root, cancel } = getUi();
  root?.toggleAttribute('data-busy', busy);
  root?.querySelectorAll('[data-action-id]').forEach(button => {
    button.disabled = busy;
  });
  if (cancel) cancel.hidden = !busy;
}

function createUi() {
  if (document.getElementById(ROOT_ID)) return;

  const root = element('div', 'tt-interaction-root');
  root.id = ROOT_ID;

  const launcher = element('button', 'tt-interaction-launcher', '行动');
  launcher.type = 'button';
  launcher.dataset.role = 'launcher';
  launcher.setAttribute('aria-expanded', 'false');

  const backdrop = element('div', 'tt-interaction-backdrop');
  backdrop.dataset.role = 'backdrop';

  const panel = element('section', 'tt-interaction-panel');
  panel.dataset.role = 'panel';
  panel.dataset.ttMobileSurface = 'fullscreen-window';
  panel.setAttribute('aria-label', '暂停式交互面板');

  const header = element('header', 'tt-interaction-header');
  const title = element('div', 'tt-interaction-title', '行动面板');
  const controls = element('div', 'tt-interaction-controls');
  const retry = element('button', '', '重试回合');
  retry.type = 'button';
  retry.dataset.role = 'retry';
  retry.hidden = true;
  const cancel = element('button', '', '取消');
  cancel.type = 'button';
  cancel.dataset.role = 'cancel';
  cancel.hidden = true;
  const close = element('button', '', '关闭');
  close.type = 'button';
  close.dataset.role = 'close';
  controls.append(retry, cancel, close);
  header.append(title, controls);

  const status = element('div', 'tt-interaction-status', '尚未载入');
  status.dataset.role = 'status';
  const summary = element('div', 'tt-interaction-summary');
  summary.dataset.role = 'summary';
  const map = element('div', 'tt-interaction-map');
  map.dataset.role = 'map';

  const targetSection = element('section', 'tt-interaction-section');
  targetSection.append(element('h3', '', '目标'));
  const targets = element('div', 'tt-interaction-targets');
  targets.dataset.role = 'targets';
  targetSection.append(targets);

  const actionSection = element('section', 'tt-interaction-section');
  actionSection.append(element('h3', '', '行动'));
  const actions = element('div', 'tt-interaction-actions');
  actions.dataset.role = 'actions';
  actionSection.append(actions);

  const loreSection = element('section', 'tt-interaction-section');
  loreSection.append(element('h3', '', '本轮设定'));
  const lore = element('div', 'tt-interaction-lore');
  lore.dataset.role = 'lore';
  loreSection.append(lore);

  panel.append(header, status, summary, map, targetSection, actionSection, loreSection);
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
      readSkillText('assets/actions.yaml'),
      readSkillText('assets/regions.yaml'),
      readSkillText('assets/map.svg', true)
    ]);
    runtime.baseActions = parseYaml(actionsText).actions ?? [];
    runtime.regions = parseYaml(regionsText).regions ?? [];
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
  runtime.lastActionRecord = `[交互行动] ${JSON.stringify(record)}`;
  await startRun(true);
}

async function sendActionRecord(text) {
  const context = stContext();
  if (!context?.executeSlashCommandsWithOptions) {
    throw new Error('当前 SillyTavern 上下文无法写入玩家行动');
  }
  const command = `/send compact=true ${JSON.stringify(text)}`;
  const result = await context.executeSlashCommandsWithOptions(command, {
    handleParserErrors: false,
    handleExecutionErrors: false,
    source: `${config.projectId}-interaction`
  });
  if (result?.isError || result?.isAborted) {
    throw new Error(result.errorMessage || result.abortReason || '玩家行动写入失败');
  }
}

async function startRun(writeAction) {
  if (runtime.busy || !runtime.lastActionRecord) return;
  const agent = ttApi()?.agent;
  if (!agent?.startRunFromLegacyGenerate || !agent?.subscribe) {
    setStatus('当前版本未提供 Agent Host API，无法启动交互回合', 'error');
    return;
  }

  setBusy(true);
  const { retry } = getUi();
  if (retry) retry.hidden = true;
  setStatus(writeAction ? '记录玩家行动…' : '重新启动本回合…', 'busy');

  try {
    if (writeAction && agent.profiles?.load) {
      const loaded = await agent.profiles.load({ profileId: config.profileId });
      if (!loaded?.profile) {
        throw new Error(`未安装 Agent Profile：${config.profileId}`);
      }
    }
    if (writeAction) await sendActionRecord(runtime.lastActionRecord);
    runtime.runChatToken = currentChatToken();
    runtime.runStore = await chatStore();
    const run = await agent.startRunFromLegacyGenerate({
      generationType: 'normal',
      profileId: config.profileId,
      presentation: 'foreground',
      options: { presentation: 'foreground', stream: false }
    });
    runtime.runId = run.runId;
    setStatus('Agent 正在处理本回合…', 'busy');
    runtime.unsubscribe?.();
    runtime.unsubscribe = agent.subscribe(run.runId, event => handleRunEvent(event));
  } catch (error) {
    console.error('[TauriTavern Interaction] run start failed', error);
    setBusy(false);
    if (retry) retry.hidden = !runtime.lastActionRecord;
    setStatus(`启动失败：${error.message}`, 'error');
  }
}

async function handleRunEvent(event) {
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
    runtime.lastActionRecord = null;
    if (retry) retry.hidden = true;
    await refreshStateFromRun(runtime.runId, sameChat, runtime.runStore);
    if (sameChat) {
      await renderLore();
      setStatus('回合完成，请选择下一项行动', 'ready');
    }
  } else {
    if (!sameChat) runtime.lastActionRecord = null;
    if (retry) retry.hidden = !runtime.lastActionRecord;
    if (sameChat) {
      setStatus(PROGRESS_LABELS[event.type], event.type === 'run_failed' ? 'error' : 'idle');
    }
  }
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
    const state = parseYaml(file.text);
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
  if (!store?.getJson) return;
  try {
    const cached = await store.getJson({
      namespace: config.cacheNamespace,
      key: 'interaction-state'
    });
    if (cached?.state) runtime.state = cached.state;
  } catch {
    // Missing cache is expected on a new chat.
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
