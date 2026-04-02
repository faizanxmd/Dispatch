const STORAGE_KEYS = {
    history: 'dispatchHistory',
    settings: 'dispatchSettings',
    selectedEntryId: 'dispatchSelectedEntryId',
};

const DEFAULT_SETTINGS = {
    organizationName: 'Dispatch AI',
    nodeId: 'Router Node 01',
    region: 'US-East-1',
    timezone: 'UTC+5:30 (IST)',
    systemPrompt: 'You are a helpful assistant.',
    compactSidebar: false,
    showTokens: true,
    animations: true,
    strategy: 'Auto-Select (Recommended)',
    fallbackModel: 'Amazon Nova Pro',
    maxLatency: 150,
    rateLimit: true,
    autoFailover: true,
    costCap: false,
    defaultRefinement: 'brief',
};

const MODEL_CATALOG = [
    {
        id: 'zai.glm-5',
        name: 'Z.AI GLM 5',
        tier: 'Tier 3 — Strong Reasoning',
        tierColor: '#f28b82',
        provider: 'Z.AI',
        providerId: 'zai.glm-5',
        description: 'Used for deeper reasoning, architecture, and multi-step planning.',
        role: 'Strong Reasoning',
        costLabel: 'Premium',
    },
    {
        id: 'amazon.nova-pro-v1:0',
        name: 'Amazon Nova Pro',
        tier: 'Tier 2 — Code + Failover',
        tierColor: '#fbbc04',
        provider: 'Amazon',
        providerId: 'amazon.nova-pro-v1:0',
        description: 'Used for code-heavy prompts and as the main failover path.',
        role: 'Code / Failover',
        costLabel: 'Moderate',
    },
    {
        id: 'moonshotai.kimi-k2.5',
        name: 'Moonshot Kimi K2.5',
        tier: 'Tier 1 — Safe Reasoning',
        tierColor: '#81c995',
        provider: 'Moonshot AI',
        providerId: 'moonshotai.kimi-k2.5',
        description: 'Used for safe reasoning, ambiguous prompts, and fallback responses.',
        role: 'Ambiguous Recovery',
        costLabel: 'Balanced',
    },
    {
        id: 'mistral.ministral-3-8b-instruct',
        name: 'Mistral Ministral 3 8B',
        tier: 'Tier 0.5 — Cheap General',
        tierColor: '#d7aefb',
        provider: 'Mistral AI',
        providerId: 'mistral.ministral-3-8b-instruct',
        description: 'Used for lightweight general prompts when a cheaper route is enough.',
        role: 'Cheap General',
        costLabel: 'Low',
    },
    {
        id: 'amazon.nova-micro-v1:0',
        name: 'Amazon Nova Micro',
        tier: 'Tier 0 — Simple Queries',
        tierColor: '#a8c7fa',
        provider: 'Amazon',
        providerId: 'amazon.nova-micro-v1:0',
        description: 'Used for short factual prompts, basic math, and low-cost routing.',
        role: 'Cheap Factual',
        costLabel: 'Very Low',
    },
    {
        id: 'qwen.qwen3-next-80b-a3b',
        name: 'Qwen 3 Next 80B A3B',
        tier: 'Classifier Layer',
        tierColor: '#9aa0a6',
        provider: 'Qwen',
        providerId: 'qwen.qwen3-next-80b-a3b',
        description: 'Classifier only. Runs on ambiguous prompts and returns structured routing signals.',
        role: 'Classifier Only',
        costLabel: 'Classifier',
    },
];

const MODEL_MAP = Object.fromEntries(MODEL_CATALOG.map((model) => [model.id, model]));
const LEGACY_MODEL_NAME_TO_ID = {
    'Claude Sonnet 4.6': 'zai.glm-5',
    'Claude Haiku 4.5': 'moonshotai.kimi-k2.5',
    'Amazon Nova Pro': 'amazon.nova-pro-v1:0',
    'Amazon Nova Micro': 'amazon.nova-micro-v1:0',
    'Mistral Ministral 3B': 'mistral.ministral-3-8b-instruct',
    'Mistral Ministral 3 8B': 'mistral.ministral-3-8b-instruct',
    'Moonshot Kimi K2.5': 'moonshotai.kimi-k2.5',
    'Z.AI GLM 5': 'zai.glm-5',
};

const TEXT_ATTACHMENT_EXTENSIONS = new Set([
    'txt', 'md', 'py', 'js', 'ts', 'tsx', 'jsx', 'json', 'html', 'css',
    'csv', 'xml', 'yaml', 'yml', 'java', 'c', 'cpp', 'h', 'hpp', 'rs',
    'go', 'sql', 'sh', 'log',
]);
const MAX_ATTACHMENT_CHARS = 12000;
const PREMIUM_BENCHMARK = {
    id: 'anthropic.claude-sonnet-4-6-benchmark',
    name: 'Claude Sonnet 4.6',
    inputPricePerMillion: 3.0,
    outputPricePerMillion: 15.0,
};

const MODEL_PRICE_PROFILES = {
    'amazon.nova-micro-v1:0': { inputPricePerMillion: 0.035, outputPricePerMillion: 0.14 },
    'mistral.ministral-3-8b-instruct': { inputPricePerMillion: 0.1, outputPricePerMillion: 0.3 },
    'moonshotai.kimi-k2.5': { inputPricePerMillion: 0.6, outputPricePerMillion: 3.0 },
    'amazon.nova-pro-v1:0': { inputPricePerMillion: 0.8, outputPricePerMillion: 3.2 },
    'zai.glm-5': { inputPricePerMillion: 0.6, outputPricePerMillion: 2.5 },
    'qwen.qwen3-next-80b-a3b': { inputPricePerMillion: 0.12, outputPricePerMillion: 0.6 },
    [PREMIUM_BENCHMARK.id]: {
        inputPricePerMillion: PREMIUM_BENCHMARK.inputPricePerMillion,
        outputPricePerMillion: PREMIUM_BENCHMARK.outputPricePerMillion,
    },
};

const PRACTICAL_BENCHMARK_CANDIDATES_BY_MODEL = {
    'amazon.nova-micro-v1:0': ['mistral.ministral-3-8b-instruct', 'moonshotai.kimi-k2.5', 'zai.glm-5', PREMIUM_BENCHMARK.id],
    'mistral.ministral-3-8b-instruct': ['moonshotai.kimi-k2.5', 'zai.glm-5', PREMIUM_BENCHMARK.id],
    'moonshotai.kimi-k2.5': ['zai.glm-5', PREMIUM_BENCHMARK.id],
    'amazon.nova-pro-v1:0': ['zai.glm-5', PREMIUM_BENCHMARK.id],
    'zai.glm-5': [PREMIUM_BENCHMARK.id],
    'qwen.qwen3-next-80b-a3b': ['moonshotai.kimi-k2.5', 'zai.glm-5', PREMIUM_BENCHMARK.id],
};

let analyticsChart = null;
let pendingAttachments = [];

document.addEventListener('DOMContentLoaded', () => {
    migrateHistory();
    initDotGrid();
    initSidebar();
    hydrateAvatar();
    initRefinementMenu();
    renderSidebarHistory();
    initIndexPage();
    initHistoryPage();
    initAnalyticsPage();
    initModelsPage();
    initSettingsPage();
    initProfilePage();
    bindGlobalButtons();
});

function initDotGrid() {
    const dotGridInteractive = document.getElementById('dot-grid-interactive');
    if (!dotGridInteractive) return;

    document.addEventListener('mousemove', (event) => {
        dotGridInteractive.style.setProperty('--mouse-x', `${event.clientX}px`);
        dotGridInteractive.style.setProperty('--mouse-y', `${event.clientY}px`);
    });
}

function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const collapseBtn = document.getElementById('sidebar-collapse-btn');
    if (!sidebar) return;

    const settings = getSettings();
    const shouldCollapse = localStorage.getItem('sidebarCollapsed');
    const collapsed = shouldCollapse === null ? settings.compactSidebar : shouldCollapse === 'true';
    sidebar.classList.toggle('collapsed', collapsed);

    if (collapseBtn) {
        collapseBtn.addEventListener('click', () => {
            const isCollapsed = sidebar.classList.toggle('collapsed');
            localStorage.setItem('sidebarCollapsed', String(isCollapsed));
        });
    }
}

function hydrateAvatar() {
    const settings = getSettings();
    const avatars = document.querySelectorAll('#user-avatar');
    const avatarLetter = (settings.organizationName || 'Dispatch').trim().charAt(0).toUpperCase() || 'D';
    avatars.forEach((avatar) => {
        avatar.textContent = avatarLetter;
        avatar.title = settings.organizationName;
    });
}

function bindGlobalButtons() {
    document.querySelectorAll('button').forEach((button) => {
        button.addEventListener('click', function handleRipple() {
            this.classList.remove('ripple-active');
            void this.offsetWidth;
            this.classList.add('ripple-active');
        });
    });
}

function initRefinementMenu() {
    const optionButtons = document.querySelectorAll('[data-refinement]');
    const menu = document.getElementById('options-menu');
    const trigger = document.getElementById('options-popup-btn');
    if (!optionButtons.length) return;

    let settings = getSettings();
    highlightRefinement(settings.defaultRefinement);

    if (trigger && menu) {
        trigger.addEventListener('click', (event) => {
            event.stopPropagation();
            menu.classList.toggle('open');
        });
    }

    optionButtons.forEach((button) => {
        button.addEventListener('click', () => {
            settings = { ...settings, defaultRefinement: button.dataset.refinement || 'brief' };
            saveSettings(settings);
            highlightRefinement(settings.defaultRefinement);
            if (menu) menu.classList.remove('open');

            const routeDesc = document.querySelector('.route-desc');
            if (routeDesc && !document.querySelector('.response-output')) {
                routeDesc.textContent = `Ready • ${capitalize(settings.defaultRefinement)}`;
            }
        });
    });

    document.addEventListener('click', (event) => {
        if (!menu || !trigger) return;
        if (!menu.contains(event.target) && !trigger.contains(event.target)) {
            menu.classList.remove('open');
        }
    });
}

function highlightRefinement(selectedRefinement) {
    document.querySelectorAll('[data-refinement]').forEach((button) => {
        const isActive = button.dataset.refinement === selectedRefinement;
        button.classList.toggle('refinement-option-active', isActive);
    });
}

function initIndexPage() {
    const promptInput = document.getElementById('prompt-input');
    const goBtn = document.getElementById('go-btn');
    const addBtn = document.getElementById('add-btn');
    const fileInput = document.getElementById('file-input');
    const attachmentList = document.getElementById('attachment-list');
    if (!promptInput || !goBtn) return;
    const isFreshChat = new URLSearchParams(window.location.search).get('fresh') === '1';

    promptInput.addEventListener('input', autoResizePrompt);
    promptInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            goBtn.click();
        }
    });

    if (addBtn && fileInput && attachmentList) {
        addBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', async (event) => {
            const files = Array.from(event.target.files || []);
            if (!files.length) return;
            const attachments = await Promise.all(files.map(readAttachmentFile));
            pendingAttachments = [
                ...pendingAttachments,
                ...attachments.filter(Boolean),
            ];
            renderAttachmentList(attachmentList);
            fileInput.value = '';
        });
        attachmentList.addEventListener('click', (event) => {
            const removeBtn = event.target.closest('[data-remove-attachment]');
            if (!removeBtn) return;
            pendingAttachments = pendingAttachments.filter((attachment) => attachment.id !== removeBtn.dataset.removeAttachment);
            renderAttachmentList(attachmentList);
        });
        renderAttachmentList(attachmentList);
    }

    if (isFreshChat) {
        pendingAttachments = [];
        renderAttachmentList(attachmentList);
        localStorage.removeItem(STORAGE_KEYS.selectedEntryId);
        renderIdleState();
        window.history.replaceState({}, '', 'index.html');
    } else {
        const latestEntry = getHistory()[0];
        if (latestEntry) {
            renderIndexEntry(latestEntry);
        } else {
            renderIdleState();
        }
    }

    checkBackendHealth();

    goBtn.addEventListener('click', async () => {
        const prompt = promptInput.value.trim();
        if (!prompt) {
            promptInput.focus();
            promptInput.placeholder = 'Please enter a prompt first...';
            window.setTimeout(() => {
                promptInput.placeholder = 'Enter your prompt here...';
            }, 1800);
            return;
        }

        const refinement = getSettings().defaultRefinement;
        setLoadingState(prompt, refinement);

        let payload = null;
        try {
            const promptToSend = buildPromptWithAttachments(prompt);
            const response = await fetch('/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: promptToSend, refinement }),
            });

            payload = await response.json();
            const historyEntry = saveResultToHistory(payload, prompt, refinement);
            renderSidebarHistory();
            renderIndexEntry(historyEntry);
            promptInput.value = '';
            promptInput.style.height = 'auto';
            clearPendingAttachments(attachmentList, fileInput);
        } catch (error) {
            const historyEntry = saveErrorToHistory(error, prompt, refinement, payload);
            renderSidebarHistory();
            renderIndexEntry(historyEntry);
        } finally {
            goBtn.textContent = 'GO';
            goBtn.style.pointerEvents = 'auto';
        }
    });
}

async function readAttachmentFile(file) {
    const extension = getFileExtension(file.name);
    if (!TEXT_ATTACHMENT_EXTENSIONS.has(extension)) {
        return {
            id: buildEntryId(),
            name: file.name,
            size: file.size,
            language: 'text',
            content: `[Unsupported file omitted: ${file.name}. Attach text or code files to send inline context.]`,
            truncated: false,
            unsupported: true,
        };
    }

    try {
        const rawText = await file.text();
        const text = rawText.slice(0, MAX_ATTACHMENT_CHARS);
        return {
            id: buildEntryId(),
            name: file.name,
            size: file.size,
            language: mapLanguageFromExtension(extension),
            content: text,
            truncated: rawText.length > MAX_ATTACHMENT_CHARS,
            unsupported: false,
        };
    } catch (error) {
        return {
            id: buildEntryId(),
            name: file.name,
            size: file.size,
            language: 'text',
            content: `[Could not read ${file.name}.]`,
            truncated: false,
            unsupported: true,
        };
    }
}

function renderAttachmentList(container) {
    if (!container) return;
    if (!pendingAttachments.length) {
        container.innerHTML = '';
        return;
    }

    container.innerHTML = pendingAttachments.map((attachment) => `
        <div class="attachment-chip">
            <div class="attachment-chip-copy">
                <span class="attachment-chip-name">${escapeHtml(attachment.name)}</span>
                <span class="attachment-chip-meta">${attachment.unsupported ? 'metadata only' : attachment.truncated ? `${formatBytes(attachment.size)} • trimmed` : formatBytes(attachment.size)}</span>
            </div>
            <button class="attachment-remove-btn" type="button" title="Remove file" data-remove-attachment="${escapeHtml(attachment.id)}">×</button>
        </div>
    `).join('');
}

function clearPendingAttachments(container, input) {
    pendingAttachments = [];
    if (container) renderAttachmentList(container);
    if (input) input.value = '';
}

function buildPromptWithAttachments(prompt) {
    if (!pendingAttachments.length) return prompt;

    const attachmentText = pendingAttachments.map((attachment) => {
        const header = `Attached file: ${attachment.name}${attachment.truncated ? ' (trimmed)' : ''}`;
        return `${header}\n\`\`\`${attachment.language}\n${attachment.content}\n\`\`\``;
    }).join('\n\n');

    return `${prompt}\n\nUse the attached file context if it is relevant.\n\n${attachmentText}`;
}

function autoResizePrompt(event) {
    const promptInput = event.currentTarget;
    promptInput.style.height = 'auto';
    promptInput.style.height = `${Math.min(promptInput.scrollHeight, 200)}px`;
}

function renderIdleState() {
    const routeModel = document.querySelector('.route-model');
    const routeDesc = document.querySelector('.route-desc');
    const speedValue = document.querySelector('.speed-value');
    const speedFill = document.querySelector('.speed-bar-fill');
    const responseBody = document.querySelector('.response-body');
    const responseStatus = document.querySelector('.response-status');

    if (routeModel) routeModel.textContent = 'Dispatch Router';
    if (routeDesc) routeDesc.textContent = `Ready • ${capitalize(getSettings().defaultRefinement)}`;
    if (speedValue) speedValue.textContent = '0ms';
    if (speedFill) speedFill.style.width = '0%';
    if (responseStatus) responseStatus.innerHTML = successBadge('Ready');
    if (responseBody) {
        responseBody.innerHTML = `
            <div class="response-empty">
                <p class="response-empty-title">Ready when you are.</p>
                <p class="response-empty-copy">Enter a prompt to get a routed answer.</p>
            </div>
        `;
    }
}

async function checkBackendHealth() {
    const responseStatus = document.querySelector('.response-status');
    const routeDesc = document.querySelector('.route-desc');
    const hasRenderedResult = Boolean(document.querySelector('.response-output'));
    try {
        const response = await fetch('/health');
        const payload = await response.json();
        if (payload.status && responseStatus && !hasRenderedResult) {
            responseStatus.innerHTML = successBadge('Backend Online');
        }
        if (routeDesc && !hasRenderedResult) {
            routeDesc.textContent = `Online • ${capitalize(getSettings().defaultRefinement)}`;
        }
    } catch (error) {
        if (responseStatus && !hasRenderedResult) {
            responseStatus.innerHTML = errorBadge('Backend Offline');
        }
        if (routeDesc && !hasRenderedResult) {
            routeDesc.textContent = 'Backend unavailable right now';
        }
    }
}

function setLoadingState(prompt, refinement) {
    const goBtn = document.getElementById('go-btn');
    const responseBody = document.querySelector('.response-body');
    const responseStatus = document.querySelector('.response-status');
    const routeModel = document.querySelector('.route-model');
    const routeDesc = document.querySelector('.route-desc');
    const speedValue = document.querySelector('.speed-value');
    const speedFill = document.querySelector('.speed-bar-fill');

    goBtn.textContent = '...';
    goBtn.style.pointerEvents = 'none';

    if (responseStatus) responseStatus.innerHTML = workingBadge('Routing');
    if (routeModel) routeModel.textContent = 'Routing...';
    if (routeDesc) routeDesc.textContent = `Finding route • ${capitalize(refinement)}`;
    if (speedValue) speedValue.textContent = '--';
    if (speedFill) speedFill.style.width = '18%';
    if (responseBody) {
        responseBody.innerHTML = `
            <div class="response-empty">
                <p class="response-empty-title">Routing your prompt</p>
                <p class="response-empty-copy">"${escapeHtml(truncate(prompt, 120))}"</p>
                <div class="loading-skeleton-group">
                    <div class="skeleton-line w80"></div>
                    <div class="skeleton-line w100"></div>
                    <div class="skeleton-line w90"></div>
                    <div class="skeleton-line w65"></div>
                </div>
            </div>
        `;
    }
}

function renderIndexEntry(entry) {
    const responseBody = document.querySelector('.response-body');
    const responseStatus = document.querySelector('.response-status');
    const routeModel = document.querySelector('.route-model');
    const routeDesc = document.querySelector('.route-desc');
    const speedValue = document.querySelector('.speed-value');
    const speedFill = document.querySelector('.speed-bar-fill');

    if (!responseBody || !routeModel || !routeDesc || !speedValue) return;

    routeModel.textContent = entry.modelName;
    routeDesc.textContent = buildRouteSummary(entry);
    speedValue.textContent = `${Math.round(entry.latencyMs || 0)}ms`;

    if (speedFill) {
        const threshold = getSettings().maxLatency || 150;
        const width = Math.max(12, Math.min(100, ((entry.latencyMs || 0) / threshold) * 100));
        speedFill.style.width = `${width}%`;
    }

    responseStatus.innerHTML = entry.ok ? successBadge(entry.fallbackUsed ? 'Fallback Success' : 'Success') : errorBadge('Failed');
    const sameBenchmarkAsPremium = (
        String(entry.baselineModel || '') === String(entry.premiumBaselineModel || '')
        || (
            String(entry.baselineModelName || '') === String(entry.premiumBaselineModelName || '')
            && Math.abs(Number(entry.baselineCost || 0) - Number(entry.premiumBaselineCost || 0)) < 0.000000001
        )
    );
    const baselineLabel = sameBenchmarkAsPremium
        ? `${entry.baselineModelName || 'Benchmark'} Benchmark`
        : 'Next Best Baseline';
    const premiumBenchmarkCards = sameBenchmarkAsPremium ? '' : `
                <div class="response-meta-item">
                    <span class="meta-key">Premium Benchmark</span>
                    <span class="meta-value">${formatCurrency(entry.premiumBaselineCost)}</span>
                </div>
                <div class="response-meta-item">
                    <span class="meta-key">Saved vs ${escapeHtml(entry.premiumBaselineModelName)}</span>
                    <span class="meta-value ${entry.premiumSavingsPct < 0 ? 'negative-money' : 'positive-money'}">${formatSavingsText(entry.premiumSavingsPct, entry.premiumBaselineModelName)}</span>
                </div>
    `;
    const routingExecutionCards = entry.fallbackUsed && entry.selectedModelId && entry.selectedModelId !== entry.modelId ? `
                <div class="response-meta-item">
                    <span class="meta-key">Selected by Router</span>
                    <span class="meta-value">${escapeHtml(entry.selectedModelName)}</span>
                </div>
                <div class="response-meta-item">
                    <span class="meta-key">Served by</span>
                    <span class="meta-value">${escapeHtml(entry.modelName)} (fallback)</span>
                </div>
    ` : '';
    responseBody.innerHTML = `
        <div class="response-output markdown-response">${renderMarkdown(entry.response || 'No response returned.')}</div>
        <details class="response-details">
            <summary>
                <span>Routing details</span>
                <span class="response-details-hint">Cost, tokens, Qwen, request id, and routing path</span>
            </summary>
            <div class="response-meta-grid">
                <div class="response-meta-item">
                    <span class="meta-key">Prompt</span>
                    <span class="meta-value">${escapeHtml(truncate(entry.prompt, 140))}</span>
                </div>
                <div class="response-meta-item">
                    <span class="meta-key">Task</span>
                    <span class="meta-value">${capitalize(entry.task)} / ${capitalize(entry.complexity)}</span>
                </div>
                <div class="response-meta-item">
                    <span class="meta-key">Qwen</span>
                    <span class="meta-value">${entry.usedQwen ? `Used${entry.qwenConfidence !== null ? ` (${Number(entry.qwenConfidence).toFixed(2)})` : ''}` : 'Skipped'}</span>
                </div>
                <div class="response-meta-item">
                    <span class="meta-key">Actual Cost</span>
                    <span class="meta-value">${formatCurrency(entry.cost)}</span>
                </div>
                ${routingExecutionCards}
                <div class="response-meta-item">
                    <span class="meta-key">${escapeHtml(baselineLabel)}</span>
                    <span class="meta-value">${formatCurrency(entry.baselineCost)}</span>
                </div>
                <div class="response-meta-item">
                    <span class="meta-key">Saved vs ${escapeHtml(entry.baselineModelName)}</span>
                    <span class="meta-value ${entry.savingsPct < 0 ? 'negative-money' : 'positive-money'}">${formatSavingsText(entry.savingsPct, entry.baselineModelName)}</span>
                </div>
                <div class="response-meta-item">
                    <span class="meta-key">Net Routed vs ${escapeHtml(entry.baselineModelName)}</span>
                    <span class="meta-value ${entry.netSavingsPct < 0 ? 'negative-money' : 'positive-money'}">${formatSavingsText(entry.netSavingsPct, entry.baselineModelName)}</span>
                </div>
                ${premiumBenchmarkCards}
                <div class="response-meta-item">
                    <span class="meta-key">Tokens</span>
                    <span class="meta-value">${formatNumber(entry.totalTokens)}${buildTokenSuffix(entry)}</span>
                </div>
                <div class="response-meta-item">
                    <span class="meta-key">Request ID</span>
                    <span class="meta-value mono-text">${escapeHtml(entry.requestId || 'n/a')}</span>
                </div>
                <div class="response-meta-item full-width">
                    <span class="meta-key">Reason</span>
                    <span class="meta-value">${escapeHtml(entry.reason || 'No routing reason recorded.')}</span>
                </div>
                <div class="response-meta-item full-width">
                    <span class="meta-key">Route Path</span>
                    <span class="meta-value mono-text">${escapeHtml(entry.routePath || 'No route path recorded.')}</span>
                </div>
            </div>
        </details>
    `;
    typesetMath(responseBody);
}

function buildTokenSuffix(entry) {
    if (!getSettings().showTokens) return '';
    if (!entry.promptTokens && !entry.outputTokens) return '';
    return ` (${formatNumber(entry.promptTokens)} in / ${formatNumber(entry.outputTokens)} out)`;
}

function buildRouteSummary(entry) {
    const parts = [capitalize(entry.task), capitalize(entry.complexity)];

    parts.push(entry.usedQwen ? 'Qwen' : 'Direct');

    if (entry.fallbackUsed) {
        parts.push('Fallback');
    }

    return parts.join(' • ');
}

function renderSidebarHistory() {
    const listContainer = document.getElementById('analytics-prompt-list');
    if (!listContainer) return;

    const history = getHistory();
    if (!history.length) {
        listContainer.innerHTML = '<div style="color: var(--text-secondary); text-align: center; padding: 24px; font-size: 14px;">No prompts yet.</div>';
        return;
    }

    listContainer.innerHTML = '';

    history.slice(0, 8).forEach((entry) => {
        const item = document.createElement('div');
        item.className = 'sidebar-history-item';
        item.innerHTML = `
            <div style="font-size: 13px; font-weight: 500; margin-bottom: 6px; color: var(--text-primary); text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">"${escapeHtml(truncate(entry.prompt, 48))}"</div>
            <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--text-secondary); gap: 8px;">
                <span>${escapeHtml(entry.modelName)}</span>
                <span>${escapeHtml(formatDate(entry.createdAt))}</span>
            </div>
        `;

        item.onmouseover = () => {
            item.style.background = 'rgba(255,255,255,0.05)';
            item.style.borderColor = 'var(--border-color)';
        };
        item.onmouseout = () => {
            item.style.background = 'transparent';
            item.style.borderColor = 'transparent';
        };

        item.style.padding = '12px';
        item.style.background = 'transparent';
        item.style.border = '1px solid transparent';
        item.style.borderRadius = '8px';
        item.style.cursor = 'pointer';
        item.style.transition = 'all 0.2s';

        item.onclick = () => {
            setSelectedEntryId(entry.id);
            const promptInput = document.getElementById('prompt-input');
            const analyticsChartCanvas = document.getElementById('performanceChart');
            if (promptInput) {
                promptInput.value = entry.prompt;
                promptInput.focus();
                promptInput.style.height = 'auto';
                promptInput.style.height = `${Math.min(promptInput.scrollHeight, 200)}px`;
                renderIndexEntry(entry);
                return;
            }
            if (analyticsChartCanvas) {
                renderAnalyticsPage();
                return;
            }
            window.location.href = `analytics.html?entry=${encodeURIComponent(entry.id)}`;
        };

        listContainer.appendChild(item);
    });
}

function initHistoryPage() {
    const historyList = document.getElementById('history-list');
    const clearBtn = document.getElementById('history-clear-btn');
    if (!historyList) return;

    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            if (!window.confirm('Clear all saved routing history?')) return;
            clearHistory();
            renderSidebarHistory();
            renderHistoryPage();
        });
    }

    renderHistoryPage();
}

function renderHistoryPage() {
    const historyList = document.getElementById('history-list');
    if (!historyList) return;

    const history = getHistory();
    if (!history.length) {
        historyList.innerHTML = '<div class="history-empty">No history found yet. Run a few prompts from the main page to populate this view.</div>';
        return;
    }

    historyList.innerHTML = history
        .map((entry) => {
            const chips = [
                `${Math.round(entry.latencyMs || 0)}ms`,
                formatCurrency(entry.cost),
                formatSavingsChip(entry.savingsPct),
                entry.usedQwen ? 'Qwen' : 'Direct',
            ];

            if (entry.fallbackUsed) {
                chips.push('Failover');
            }

            return `
                <div class="model-card history-card" data-entry-id="${escapeHtml(entry.id)}" style="cursor: pointer; transition: background 0.2s;">
                    <div class="model-header">
                        <h3 class="model-title">${escapeHtml(truncate(entry.prompt, 46))}</h3>
                        <span class="model-tier" style="color: var(--text-secondary); font-size: 12px; font-weight: 400;">${escapeHtml(formatDateTime(entry.createdAt))}</span>
                    </div>
                    <p class="model-desc">${escapeHtml(truncate(entry.response || entry.reason || 'No response recorded.', 180))}</p>
                    <div class="history-chip-row">${chips.map((chip) => `<span class="history-chip">${escapeHtml(chip)}</span>`).join('')}</div>
                    <span class="model-provider" style="margin-top: 12px; display: inline-block;">Routed to: ${escapeHtml(entry.modelName)} • ${escapeHtml(capitalize(entry.task))} / ${escapeHtml(capitalize(entry.complexity))}</span>
                </div>
            `;
        })
        .join('');

    historyList.querySelectorAll('.history-card').forEach((card) => {
        card.addEventListener('click', () => {
            const entryId = card.dataset.entryId;
            setSelectedEntryId(entryId);
            window.location.href = `analytics.html?entry=${encodeURIComponent(entryId)}`;
        });
    });
}

function initAnalyticsPage() {
    const chartCanvas = document.getElementById('performanceChart');
    const clearBtn = document.getElementById('clear-history-btn');
    if (!chartCanvas) return;

    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            if (!window.confirm('Are you sure you want to clear your prompt history?')) return;
            clearHistory();
            renderSidebarHistory();
            renderAnalyticsPage();
        });
    }

    renderAnalyticsPage();
}

function renderAnalyticsPage() {
    const history = getHistory();
    const selectedTitle = document.getElementById('selected-prompt-title');
    const chartPlaceholder = document.getElementById('chart-placeholder');
    const chartCanvas = document.getElementById('performanceChart');
    const totalSavings = document.getElementById('stat-total-savings');
    const totalSavingsDetail = document.getElementById('stat-total-savings-detail');
    const statModel = document.getElementById('stat-model');
    const statLatency = document.getElementById('stat-latency');
    const statCost = document.getElementById('stat-cost');
    const statBaselineCost = document.getElementById('stat-baseline-cost');
    const statSavings = document.getElementById('stat-savings');
    if (!selectedTitle || !chartPlaceholder || !chartCanvas || !totalSavings || !totalSavingsDetail || !statModel || !statLatency || !statCost || !statBaselineCost || !statSavings) return;

    if (!history.length) {
        selectedTitle.textContent = 'Select a prompt to view analytics';
        chartPlaceholder.style.display = 'block';
        chartCanvas.style.display = 'none';
        totalSavings.textContent = `$0 saved`;
        totalSavingsDetail.textContent = `Model-only benchmark vs next-best model`;
        statModel.textContent = '-';
        statLatency.textContent = '0ms';
        statCost.textContent = '$0';
        statBaselineCost.textContent = '$0';
        statSavings.textContent = 'Matches next-best model';
        if (analyticsChart) analyticsChart.destroy();
        return;
    }

    const selected = getSelectedEntry(history);
    if (!selected) return;
    const totals = buildHistoryTotals(history);

    selectedTitle.textContent = `Analytics for: ${truncate(selected.prompt, 52)}`;
    totalSavings.textContent = formatSavingsAmount(totals.savedAmount, 'next-best models');
    totalSavingsDetail.textContent = `Model-only ${formatCompactCurrency(totals.modelCost)} • Next-best ${formatCompactCurrency(totals.baselineCost)} • Premium ref ${formatSavingsAmount(totals.premiumSavedAmount, PREMIUM_BENCHMARK.name)}`;
    totalSavings.style.color = totals.savedAmount < 0 ? '#f28b82' : '#81c995';
    statModel.textContent = selected.modelName;
    statLatency.textContent = `${Math.round(selected.latencyMs || 0)}ms`;
    statCost.textContent = formatCompactCurrency(selected.cost);
    statBaselineCost.textContent = formatCompactCurrency(selected.baselineCost);
    statSavings.textContent = formatSavingsText(selected.savingsPct, selected.baselineModelName);
    statSavings.style.color = selected.savingsPct < 0 ? '#f28b82' : '#81c995';
    chartPlaceholder.style.display = 'none';
    chartCanvas.style.display = 'block';

    if (!window.Chart) return;

    const recentEntries = history.slice(0, 8).reverse();
    const labels = recentEntries.map((entry, index) => {
        const labelSeed = entry.modelName.split(' ').slice(0, 2).join(' ');
        return `${index + 1}. ${labelSeed}`;
    });
    const latencies = recentEntries.map((entry) => Math.round(entry.latencyMs || 0));
    const backgroundColor = recentEntries.map((entry) => (
        entry.id === selected.id ? 'rgba(129, 201, 149, 0.65)' : 'rgba(168, 199, 250, 0.18)'
    ));
    const borderColor = recentEntries.map((entry) => (
        entry.id === selected.id ? '#81c995' : 'rgba(168, 199, 250, 0.38)'
    ));

    if (analyticsChart) analyticsChart.destroy();

    analyticsChart = new window.Chart(chartCanvas.getContext('2d'), {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Latency (ms)',
                    data: latencies,
                    backgroundColor,
                    borderColor,
                    borderWidth: 1,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: { color: 'rgba(255, 255, 255, 0.8)' },
                },
                tooltip: {
                    callbacks: {
                        afterLabel(context) {
                            const entry = recentEntries[context.dataIndex];
                            return [
                                `Model: ${entry.modelName}`,
                                `Cost: ${formatCurrency(entry.cost)}`,
                                `Next-best baseline: ${formatCurrency(entry.baselineCost)}`,
                                `${entry.baselineModelName} comparison: ${formatSavingsText(entry.savingsPct, entry.baselineModelName)}`,
                                `${entry.premiumBaselineModelName} comparison: ${formatSavingsText(entry.premiumSavingsPct, entry.premiumBaselineModelName)}`,
                                `Qwen: ${entry.usedQwen ? 'Yes' : 'No'}`,
                            ];
                        },
                    },
                },
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: 'rgba(255,255,255,0.6)' },
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: 'rgba(255,255,255,0.6)' },
                },
            },
        },
    });
}

function initModelsPage() {
    const modelsList = document.getElementById('models-list');
    const addModelBtn = document.getElementById('add-model-btn');
    if (!modelsList) return;

    modelsList.innerHTML = MODEL_CATALOG.map((model) => `
        <div class="model-card">
            <div class="model-header">
                <h3 class="model-title">${escapeHtml(model.name)}</h3>
                <span class="model-tier" style="color: ${model.tierColor};">${escapeHtml(model.tier)}</span>
            </div>
            <span class="model-provider">${escapeHtml(model.providerId)} • Provider: ${escapeHtml(model.provider)} • ${escapeHtml(model.role)}</span>
            <p class="model-desc">${escapeHtml(model.description)}</p>
        </div>
    `).join('');

    if (addModelBtn) {
        addModelBtn.addEventListener('click', () => {
            window.alert('Model inventory is managed by the backend routing config. Update backend/model.py to add or replace production models.');
        });
    }
}

function initSettingsPage() {
    const saveBtn = document.getElementById('settings-save-btn');
    if (!saveBtn) return;

    const cancelBtn = document.getElementById('settings-cancel-btn');
    loadSettingsIntoForm();

    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => loadSettingsIntoForm());
    }

    saveBtn.addEventListener('click', () => {
        const settings = {
            ...getSettings(),
            organizationName: document.getElementById('settings-org-name')?.value.trim() || DEFAULT_SETTINGS.organizationName,
            nodeId: document.getElementById('settings-node-id')?.value.trim() || DEFAULT_SETTINGS.nodeId,
            region: document.getElementById('settings-region')?.value || DEFAULT_SETTINGS.region,
            timezone: document.getElementById('settings-timezone')?.value || DEFAULT_SETTINGS.timezone,
            systemPrompt: document.getElementById('settings-system-prompt')?.value.trim() || DEFAULT_SETTINGS.systemPrompt,
            compactSidebar: Boolean(document.getElementById('settings-compact-sidebar')?.checked),
            showTokens: Boolean(document.getElementById('settings-show-tokens')?.checked),
            animations: Boolean(document.getElementById('settings-animations')?.checked),
            strategy: document.getElementById('settings-strategy')?.value || DEFAULT_SETTINGS.strategy,
            fallbackModel: document.getElementById('settings-fallback-model')?.value || DEFAULT_SETTINGS.fallbackModel,
            maxLatency: Number(document.getElementById('settings-max-latency')?.value || DEFAULT_SETTINGS.maxLatency),
            rateLimit: Boolean(document.getElementById('settings-rate-limit')?.checked),
            autoFailover: Boolean(document.getElementById('settings-auto-failover')?.checked),
            costCap: Boolean(document.getElementById('settings-cost-cap')?.checked),
        };

        saveSettings(settings);
        localStorage.setItem('sidebarCollapsed', String(settings.compactSidebar));
        hydrateAvatar();

        const saveLabel = saveBtn.textContent;
        saveBtn.textContent = 'Saved';
        window.setTimeout(() => {
            saveBtn.textContent = saveLabel;
        }, 1200);
    });
}

function loadSettingsIntoForm() {
    const settings = getSettings();
    setValue('settings-org-name', settings.organizationName);
    setValue('settings-node-id', settings.nodeId);
    setValue('settings-region', settings.region);
    setValue('settings-timezone', settings.timezone);
    setValue('settings-system-prompt', settings.systemPrompt);
    setChecked('settings-compact-sidebar', settings.compactSidebar);
    setChecked('settings-show-tokens', settings.showTokens);
    setChecked('settings-animations', settings.animations);
    setValue('settings-strategy', settings.strategy);
    setValue('settings-fallback-model', settings.fallbackModel);
    setValue('settings-max-latency', settings.maxLatency);
    setChecked('settings-rate-limit', settings.rateLimit);
    setChecked('settings-auto-failover', settings.autoFailover);
    setChecked('settings-cost-cap', settings.costCap);

    const latencyLabel = document.getElementById('val-latency');
    if (latencyLabel) latencyLabel.textContent = settings.maxLatency;
}

function initProfilePage() {
    const main = document.getElementById('main-content');
    const title = main?.querySelector('h1');
    if (!main || !title || title.textContent.trim() !== 'User Profile') return;

    const settings = getSettings();
    const history = getHistory();
    const totalCost = history.reduce((sum, entry) => sum + (entry.cost || 0), 0);
    const averageLatency = history.length
        ? Math.round(history.reduce((sum, entry) => sum + (entry.latencyMs || 0), 0) / history.length)
        : 0;
    const qwenCount = history.filter((entry) => entry.usedQwen).length;
    const mostUsedModel = history.length
        ? Object.entries(history.reduce((acc, entry) => {
            acc[entry.modelName] = (acc[entry.modelName] || 0) + 1;
            return acc;
        }, {})).sort((left, right) => right[1] - left[1])[0][0]
        : 'No traffic yet';

    main.innerHTML = `
        <div class="profile-shell">
            <div class="profile-hero">
                <div class="profile-avatar-large">${escapeHtml((settings.organizationName || 'D').charAt(0).toUpperCase())}</div>
                <div>
                    <h1 style="margin: 0 0 8px;">${escapeHtml(settings.organizationName)}</h1>
                    <p style="color: var(--text-secondary); margin: 0;">${escapeHtml(settings.nodeId)} • ${escapeHtml(settings.region)} • ${escapeHtml(settings.timezone)}</p>
                </div>
            </div>
            <div class="profile-grid">
                <div class="profile-card">
                    <span class="meta-key">Total Routed Prompts</span>
                    <strong>${formatNumber(history.length)}</strong>
                </div>
                <div class="profile-card">
                    <span class="meta-key">Average Latency</span>
                    <strong>${averageLatency}ms</strong>
                </div>
                <div class="profile-card">
                    <span class="meta-key">Qwen Assisted</span>
                    <strong>${formatNumber(qwenCount)}</strong>
                </div>
                <div class="profile-card">
                    <span class="meta-key">Estimated Spend</span>
                    <strong>${formatCurrency(totalCost)}</strong>
                </div>
            </div>
            <div class="profile-summary-card">
                <span class="meta-key">Most Used Model</span>
                <p style="margin-top: 10px; font-size: 20px; font-weight: 600;">${escapeHtml(mostUsedModel)}</p>
                <p style="margin-top: 10px; color: var(--text-secondary);">Dispatch is currently configured for ${escapeHtml(settings.strategy)} with ${escapeHtml(settings.fallbackModel)} as the frontend-visible fallback target.</p>
            </div>
        </div>
    `;
}

function getSelectedEntry(history) {
    const urlId = new URLSearchParams(window.location.search).get('entry');
    const storedId = localStorage.getItem(STORAGE_KEYS.selectedEntryId);
    const targetId = urlId || storedId;
    if (!targetId) return history[0];
    return history.find((entry) => String(entry.id) === String(targetId)) || history[0];
}

function setSelectedEntryId(entryId) {
    localStorage.setItem(STORAGE_KEYS.selectedEntryId, String(entryId));
}

function getSettings() {
    try {
        return { ...DEFAULT_SETTINGS, ...(JSON.parse(localStorage.getItem(STORAGE_KEYS.settings) || '{}')) };
    } catch (error) {
        return { ...DEFAULT_SETTINGS };
    }
}

function saveSettings(settings) {
    localStorage.setItem(STORAGE_KEYS.settings, JSON.stringify(settings));
}

function getHistory() {
    try {
        const parsed = JSON.parse(localStorage.getItem(STORAGE_KEYS.history) || '[]');
        return parsed.map(normalizeHistoryEntry);
    } catch (error) {
        return [];
    }
}

function saveHistory(history) {
    const normalized = history.map(normalizeHistoryEntry).slice(0, 40);
    localStorage.setItem(STORAGE_KEYS.history, JSON.stringify(normalized));
}

function clearHistory() {
    localStorage.removeItem(STORAGE_KEYS.history);
    localStorage.removeItem(STORAGE_KEYS.selectedEntryId);
}

function migrateHistory() {
    const history = getHistory();
    saveHistory(history);
}

function saveResultToHistory(result, prompt, refinement) {
    const debug = result?.debug || {};
    const entry = normalizeHistoryEntry({
        id: result?.debug?.request_id || buildEntryId(),
        prompt: result?.prompt || prompt,
        response: result?.response || result?.error || 'No response returned.',
        ok: Boolean(result?.ok),
        createdAt: new Date().toISOString(),
        modelId: result?.model_used || debug.invoked_model_id || debug.model_id,
        selectedModelId: debug.selected_model_id || debug.fallback_from_model || debug.model_id,
        servedModelId: debug.served_model_id || result?.model_used || debug.invoked_model_id || debug.model_id,
        latencyMs: Number(debug.latency_ms || debug.model_latency_ms || 0),
        cost: Number(debug.actual_cost ?? debug.estimated_cost ?? 0),
        modelCost: Number(debug.model_estimated_cost ?? 0),
        classifierCost: Number(debug.classifier_cost ?? 0),
        baselineCost: Number(debug.baseline_cost ?? 0),
        baselineModel: debug.baseline_model || debug.practical_baseline_model,
        baselineModelName: debug.baseline_model_display_name || debug.practical_baseline_model_display_name,
        savingsPct: Number(debug.model_savings_pct ?? debug.savings_pct ?? 0),
        netSavingsPct: Number(debug.net_savings_pct ?? 0),
        savedAmount: Number(debug.model_saved_amount ?? 0),
        netSavedAmount: Number(debug.net_saved_amount ?? 0),
        premiumBaselineCost: Number(debug.premium_baseline_cost ?? 0),
        premiumBaselineModel: debug.premium_baseline_model || PREMIUM_BENCHMARK.id,
        premiumBaselineModelName: debug.premium_baseline_model_display_name || PREMIUM_BENCHMARK.name,
        premiumSavingsPct: Number(debug.premium_model_savings_pct ?? debug.premium_savings_pct ?? 0),
        premiumNetSavingsPct: Number(debug.premium_net_savings_pct ?? 0),
        premiumSavedAmount: Number(debug.premium_model_saved_amount ?? 0),
        premiumNetSavedAmount: Number(debug.premium_net_saved_amount ?? 0),
        totalTokens: Number(debug.total_token_count || 0),
        promptTokens: Number(debug.prompt_token_count || 0),
        outputTokens: Number(debug.generation_token_count || 0),
        task: debug.task,
        complexity: debug.complexity,
        prefilter: debug.prefilter,
        usedQwen: debug.used_qwen,
        reason: debug.reason || result?.error || '',
        routePath: debug.decision_path || debug.route_path,
        fallbackUsed: debug.fallback_used,
        overrides: debug.overrides,
        requestId: debug.request_id,
        refinement: debug.refinement || refinement,
        qwenConfidence: debug.qwen_confidence,
    });

    const history = [entry, ...getHistory().filter((item) => item.id !== entry.id)].slice(0, 40);
    saveHistory(history);
    setSelectedEntryId(entry.id);
    return entry;
}

function saveErrorToHistory(error, prompt, refinement, payload) {
    const debug = payload?.debug || {};
    const entry = normalizeHistoryEntry({
        id: debug.request_id || buildEntryId(),
        prompt,
        response: payload?.error || error?.message || 'Request failed before the router returned a response.',
        ok: false,
        createdAt: new Date().toISOString(),
        modelId: payload?.model_used || debug.invoked_model_id || 'router-error',
        selectedModelId: debug.selected_model_id || debug.fallback_from_model || debug.model_id || payload?.model_used || 'router-error',
        servedModelId: debug.served_model_id || payload?.model_used || debug.invoked_model_id || 'router-error',
        latencyMs: Number(debug.latency_ms || 0),
        cost: Number(debug.actual_cost ?? debug.estimated_cost ?? 0),
        modelCost: Number(debug.model_estimated_cost ?? 0),
        classifierCost: Number(debug.classifier_cost ?? 0),
        baselineCost: Number(debug.baseline_cost ?? 0),
        baselineModel: debug.baseline_model || debug.practical_baseline_model,
        baselineModelName: debug.baseline_model_display_name || debug.practical_baseline_model_display_name,
        savingsPct: Number(debug.model_savings_pct ?? debug.savings_pct ?? 0),
        netSavingsPct: Number(debug.net_savings_pct ?? 0),
        savedAmount: Number(debug.model_saved_amount ?? 0),
        netSavedAmount: Number(debug.net_saved_amount ?? 0),
        premiumBaselineCost: Number(debug.premium_baseline_cost ?? 0),
        premiumBaselineModel: debug.premium_baseline_model || PREMIUM_BENCHMARK.id,
        premiumBaselineModelName: debug.premium_baseline_model_display_name || PREMIUM_BENCHMARK.name,
        premiumSavingsPct: Number(debug.premium_model_savings_pct ?? debug.premium_savings_pct ?? 0),
        premiumNetSavingsPct: Number(debug.premium_net_savings_pct ?? 0),
        premiumSavedAmount: Number(debug.premium_model_saved_amount ?? 0),
        premiumNetSavedAmount: Number(debug.premium_net_saved_amount ?? 0),
        totalTokens: Number(debug.total_token_count || 0),
        promptTokens: Number(debug.prompt_token_count || 0),
        outputTokens: Number(debug.generation_token_count || 0),
        task: debug.task || 'general',
        complexity: debug.complexity || 'medium',
        prefilter: debug.prefilter || 'error',
        usedQwen: debug.used_qwen,
        reason: debug.reason || error?.message || 'Router request failed.',
        routePath: debug.decision_path || debug.route_path || '',
        fallbackUsed: debug.fallback_used,
        overrides: debug.overrides,
        requestId: debug.request_id,
        refinement,
        qwenConfidence: debug.qwen_confidence,
    });

    const history = [entry, ...getHistory().filter((item) => item.id !== entry.id)].slice(0, 40);
    saveHistory(history);
    setSelectedEntryId(entry.id);
    return entry;
}

function normalizeHistoryEntry(raw) {
    const prompt = raw.prompt || raw.text || '';
    const legacyModel = raw.modelName || raw.model || '';
    const mappedModelId = raw.modelId || LEGACY_MODEL_NAME_TO_ID[legacyModel] || legacyModel || 'unknown-model';
    const selectedModelId = raw.selectedModelId || raw.selected_model_id || raw.fallback_from_model || mappedModelId;
    const servedModelId = raw.servedModelId || raw.served_model_id || mappedModelId;
    const promptTokens = Number(raw.promptTokens ?? raw.prompt_token_count ?? 0);
    const outputTokens = Number(raw.outputTokens ?? raw.generation_token_count ?? 0);
    const totalTokens = Number(raw.totalTokens ?? raw.tokens ?? raw.total_token_count ?? (promptTokens + outputTokens));
    const hasStructuredPricing = raw.modelCost != null
        || raw.model_cost != null
        || raw.classifierCost != null
        || raw.classifier_cost != null
        || raw.baselineCost != null
        || raw.baseline_cost != null
        || raw.premiumBaselineCost != null
        || raw.premium_baseline_cost != null;
    const legacyCost = raw.cost != null && !hasStructuredPricing && totalTokens
        ? Number(raw.cost) / 1_000_000 * totalTokens
        : Number(raw.cost ?? 0);
    const actualCost = Number(raw.actualCost ?? raw.actual_cost ?? raw.estimatedCost ?? raw.estimated_cost ?? legacyCost ?? 0);
    const modelCost = Number(raw.modelCost ?? raw.model_cost ?? actualCost ?? 0);
    const classifierCost = Number(raw.classifierCost ?? raw.classifier_cost ?? Math.max(0, actualCost - modelCost));
    const computedPracticalBenchmarkModel = getPracticalBenchmarkModelId(mappedModelId, promptTokens, outputTokens);
    const computedPracticalBenchmarkCost = estimateCostForModel(computedPracticalBenchmarkModel, promptTokens, outputTokens);
    const rawBaselineModel = raw.baselineModel || raw.baseline_model;
    const hasMatchingPracticalBaseline = rawBaselineModel === computedPracticalBenchmarkModel;
    const resolvedBaselineModel = hasMatchingPracticalBaseline ? rawBaselineModel : computedPracticalBenchmarkModel;
    const resolvedPremiumBaselineModel = raw.premiumBaselineModel || raw.premium_baseline_model || PREMIUM_BENCHMARK.id;
    const rawBaselineCost = Number(raw.baselineCost ?? raw.baseline_cost ?? NaN);
    const computedPremiumBaselineCost = estimateCostForModel(resolvedPremiumBaselineModel, promptTokens, outputTokens);
    const rawPremiumBaselineCost = Number(raw.premiumBaselineCost ?? raw.premium_baseline_cost ?? NaN);
    const baselineCost = hasMatchingPracticalBaseline && Number.isFinite(rawBaselineCost) && rawBaselineCost > 0
        ? rawBaselineCost
        : computedPracticalBenchmarkCost;
    const premiumBaselineCost = Number.isFinite(rawPremiumBaselineCost) && rawPremiumBaselineCost > 0
        ? rawPremiumBaselineCost
        : computedPremiumBaselineCost;
    const savingsPct = baselineCost
        ? ((baselineCost - modelCost) / baselineCost) * 100
        : Number(raw.savingsPct ?? raw.savings_pct ?? 0);
    const netSavingsPct = baselineCost
        ? ((baselineCost - actualCost) / baselineCost) * 100
        : Number(raw.netSavingsPct ?? raw.net_savings_pct ?? 0);
    const savedAmount = baselineCost - modelCost;
    const netSavedAmount = baselineCost - actualCost;
    const premiumSavingsPct = premiumBaselineCost
        ? ((premiumBaselineCost - modelCost) / premiumBaselineCost) * 100
        : Number(raw.premiumSavingsPct ?? raw.premium_savings_pct ?? 0);
    const premiumNetSavingsPct = premiumBaselineCost
        ? ((premiumBaselineCost - actualCost) / premiumBaselineCost) * 100
        : Number(raw.premiumNetSavingsPct ?? raw.premium_net_savings_pct ?? 0);
    const premiumSavedAmount = premiumBaselineCost - modelCost;
    const premiumNetSavedAmount = premiumBaselineCost - actualCost;

    return {
        id: raw.id || raw.requestId || raw.request_id || buildEntryId(),
        prompt,
        response: raw.response || raw.output || raw.error || '',
        ok: raw.ok !== false,
        createdAt: raw.createdAt || raw.timestamp || new Date().toISOString(),
        modelId: servedModelId,
        modelName: raw.modelName || formatModelName(servedModelId),
        selectedModelId,
        selectedModelName: raw.selectedModelName || raw.selected_model_display_name || formatModelName(selectedModelId),
        servedModelId,
        servedModelName: raw.servedModelName || raw.served_model_display_name || formatModelName(servedModelId),
        latencyMs: Number(raw.latencyMs ?? raw.latency ?? raw.latency_ms ?? 0),
        cost: actualCost,
        modelCost,
        classifierCost,
        baselineCost,
        baselineModel: resolvedBaselineModel,
        baselineModelName: hasMatchingPracticalBaseline
            ? raw.baselineModelName || raw.baseline_model_display_name || formatModelName(resolvedBaselineModel)
            : formatModelName(resolvedBaselineModel),
        savingsPct,
        netSavingsPct,
        savedAmount,
        netSavedAmount,
        premiumBaselineCost,
        premiumBaselineModel: resolvedPremiumBaselineModel,
        premiumBaselineModelName: raw.premiumBaselineModelName || raw.premium_baseline_model_display_name || PREMIUM_BENCHMARK.name,
        premiumSavingsPct,
        premiumNetSavingsPct,
        premiumSavedAmount,
        premiumNetSavedAmount,
        totalTokens,
        promptTokens,
        outputTokens,
        task: raw.task || 'general',
        complexity: raw.complexity || 'medium',
        prefilter: raw.prefilter || 'unknown',
        usedQwen: Boolean(raw.usedQwen ?? raw.used_qwen ?? false),
        reason: raw.reason || '',
        routePath: raw.routePath || raw.decisionPath || raw.decision_path || raw.route_path || '',
        fallbackUsed: Boolean(raw.fallbackUsed ?? raw.fallback_used ?? false),
        overrides: Array.isArray(raw.overrides) ? raw.overrides : [],
        requestId: raw.requestId || raw.request_id || '',
        refinement: raw.refinement || DEFAULT_SETTINGS.defaultRefinement,
        qwenConfidence: raw.qwenConfidence ?? raw.qwen_confidence ?? null,
    };
}

function successBadge(label) {
    return `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="#34a853"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
        ${escapeHtml(label)}
    `;
}

function errorBadge(label) {
    return `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="#f28b82"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>
        ${escapeHtml(label)}
    `;
}

function workingBadge(label) {
    return `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="#a8c7fa"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6a6 6 0 0 1-6 6 6 6 0 0 1-5.65-4H4.26A8 8 0 0 0 12 20a8 8 0 0 0 0-16z"/></svg>
        ${escapeHtml(label)}
    `;
}

function formatModelName(modelId) {
    if (modelId === PREMIUM_BENCHMARK.id) {
        return PREMIUM_BENCHMARK.name;
    }
    return MODEL_MAP[modelId]?.name || modelId || 'Unknown Model';
}

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

function truncate(value, maxLength) {
    const stringValue = String(value ?? '');
    if (stringValue.length <= maxLength) return stringValue;
    return `${stringValue.slice(0, Math.max(0, maxLength - 1)).trimEnd()}...`;
}

function capitalize(value) {
    const stringValue = String(value ?? '');
    if (!stringValue) return 'Unknown';
    return stringValue.charAt(0).toUpperCase() + stringValue.slice(1);
}

function formatNumber(value) {
    return new Intl.NumberFormat().format(Number(value || 0));
}

function formatBytes(value) {
    const bytes = Number(value || 0);
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileExtension(filename) {
    const parts = String(filename || '').toLowerCase().split('.');
    return parts.length > 1 ? parts.pop() : '';
}

function mapLanguageFromExtension(extension) {
    const languageMap = {
        py: 'python',
        js: 'javascript',
        jsx: 'jsx',
        ts: 'typescript',
        tsx: 'tsx',
        md: 'markdown',
        yml: 'yaml',
        h: 'c',
        hpp: 'cpp',
        rs: 'rust',
        sh: 'bash',
        txt: 'text',
    };
    return languageMap[extension] || extension || 'text';
}

function formatCurrency(value) {
    const amount = Number(value || 0);
    if (amount === 0) return '$0.000000';
    if (amount >= 1) return `$${amount.toFixed(2)}`;
    if (amount >= 0.01) return `$${amount.toFixed(4)}`;
    if (amount >= 0.0001) return `$${amount.toFixed(6)}`;
    return `$${amount.toFixed(8)}`;
}

function formatCompactCurrency(value) {
    const amount = Number(value || 0);
    if (amount === 0) return '$0';
    if (amount >= 1) return `$${amount.toFixed(2)}`;
    if (amount >= 0.01) return `$${amount.toFixed(4).replace(/0+$/u, '').replace(/\.$/u, '')}`;
    if (amount >= 0.000001) return `$${amount.toFixed(6).replace(/0+$/u, '').replace(/\.$/u, '')}`;
    return '<$0.000001';
}

function formatPercent(value) {
    return `${Number(value || 0).toFixed(2)}%`;
}

function formatSavingsText(value, baselineName = 'the benchmark') {
    const savings = Number(value || 0);
    if (Math.abs(savings) < 0.005) {
        return `Matches ${baselineName}`;
    }
    if (savings >= 0) {
        return `Saved ${formatPercent(savings)} vs ${baselineName}`;
    }
    return `${formatPercent(Math.abs(savings))} over ${baselineName}`;
}

function formatSavingsChip(value) {
    const savings = Number(value || 0);
    if (Math.abs(savings) < 0.005) {
        return 'Near baseline';
    }
    if (savings >= 0) {
        return `Save ${formatPercent(savings)}`;
    }
    return `${formatPercent(Math.abs(savings))} over`;
}

function formatSavingsAmount(savedAmount, baselineName = 'the benchmark') {
    const amount = Number(savedAmount || 0);
    if (Math.abs(amount) < 0.0000005) {
        return `On par with ${baselineName}`;
    }
    if (amount >= 0) {
        return `${formatCompactCurrency(amount)} saved`;
    }
    return `${formatCompactCurrency(Math.abs(amount))} over`;
}

function getPracticalBenchmarkModelId(modelId, promptTokens = 0, outputTokens = 0) {
    const candidates = PRACTICAL_BENCHMARK_CANDIDATES_BY_MODEL[modelId];
    if (!candidates || !candidates.length) {
        return PREMIUM_BENCHMARK.id;
    }

    const modelCost = estimateCostForModel(modelId, promptTokens, outputTokens);
    for (const candidate of candidates) {
        if (estimateCostForModel(candidate, promptTokens, outputTokens) > modelCost) {
            return candidate;
        }
    }

    return candidates[candidates.length - 1];
}

function estimateCostForModel(modelId, promptTokens, outputTokens) {
    const profile = MODEL_PRICE_PROFILES[modelId];
    if (!profile) return 0;
    const inputCount = Number(promptTokens || 0);
    const outputCount = Number(outputTokens || 0);
    return (
        (inputCount / 1_000_000) * profile.inputPricePerMillion
        + (outputCount / 1_000_000) * profile.outputPricePerMillion
    );
}

function buildHistoryTotals(history) {
    const actualCost = history.reduce((sum, entry) => sum + Number(entry.cost || 0), 0);
    const modelCost = history.reduce((sum, entry) => sum + Number(entry.modelCost || entry.cost || 0), 0);
    const baselineCost = history.reduce((sum, entry) => sum + Number(entry.baselineCost || 0), 0);
    const premiumBaselineCost = history.reduce((sum, entry) => sum + Number(entry.premiumBaselineCost || 0), 0);
    const savedAmount = baselineCost - modelCost;
    const netSavedAmount = baselineCost - actualCost;
    const premiumSavedAmount = premiumBaselineCost - modelCost;
    const premiumNetSavedAmount = premiumBaselineCost - actualCost;
    const savedPct = baselineCost ? (savedAmount / baselineCost) * 100 : 0;
    const netSavedPct = baselineCost ? (netSavedAmount / baselineCost) * 100 : 0;
    const premiumSavedPct = premiumBaselineCost ? (premiumSavedAmount / premiumBaselineCost) * 100 : 0;
    const premiumNetSavedPct = premiumBaselineCost ? (premiumNetSavedAmount / premiumBaselineCost) * 100 : 0;
    return {
        actualCost,
        modelCost,
        baselineCost,
        premiumBaselineCost,
        savedAmount,
        savedPct,
        netSavedAmount,
        netSavedPct,
        premiumSavedAmount,
        premiumSavedPct,
        premiumNetSavedAmount,
        premiumNetSavedPct,
    };
}

function renderMarkdown(markdown) {
    const source = String(markdown ?? '').replace(/\r\n?/g, '\n').trim();
    if (!source) {
        return '<p>No response returned.</p>';
    }

    const codeBlocks = [];
    const withPlaceholders = source.replace(/```([\w-]+)?\n?([\s\S]*?)```/g, (_match, language = '', code = '') => {
        const token = `@@CODEBLOCK${codeBlocks.length}@@`;
        const label = language ? escapeHtml(language) : 'text';
        const escapedCode = escapeHtml(code.replace(/\n$/, ''));
        codeBlocks.push(`
            <pre class="response-code-block"><div class="response-code-label">${label}</div><code>${escapedCode}</code></pre>
        `);
        return `\n${token}\n`;
    });

    const rendered = withPlaceholders
        .split(/\n{2,}/)
        .map((block) => renderMarkdownBlock(block))
        .filter(Boolean)
        .join('');

    return rendered.replace(/@@CODEBLOCK(\d+)@@/g, (_match, index) => codeBlocks[Number(index)] || '');
}

function renderMarkdownBlock(block) {
    const trimmed = String(block ?? '').trim();
    if (!trimmed) return '';

    if (/^@@CODEBLOCK\d+@@$/.test(trimmed)) {
        return trimmed;
    }

    const lines = trimmed.split('\n');

    if (lines.every((line) => /^[-*]\s+/.test(line))) {
        const items = lines.map((line) => line.replace(/^[-*]\s+/, ''));
        return `<ul>${items.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</ul>`;
    }

    if (lines.every((line) => /^\d+\.\s+/.test(line))) {
        const items = lines.map((line) => line.replace(/^\d+\.\s+/, ''));
        return `<ol>${items.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</ol>`;
    }

    if (lines.every((line) => /^>\s?/.test(line))) {
        return `<blockquote>${lines.map((line) => renderInlineMarkdown(line.replace(/^>\s?/, ''))).join('<br>')}</blockquote>`;
    }

    const heading = trimmed.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
        const level = Math.min(6, heading[1].length);
        return `<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`;
    }

    return `<p>${lines.map((line) => renderInlineMarkdown(line)).join('<br>')}</p>`;
}

function renderInlineMarkdown(text) {
    let rendered = escapeHtml(text ?? '');
    rendered = rendered.replace(/`([^`]+)`/g, '<code class="response-inline-code">$1</code>');
    rendered = rendered.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    return rendered;
}

function typesetMath(container) {
    if (!container || !window.MathJax?.typesetPromise) return;
    window.MathJax.typesetClear?.([container]);
    window.MathJax.typesetPromise([container]).catch(() => {});
}

function formatDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Unknown';
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function formatDateTime(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Unknown';
    return date.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
    });
}

function buildEntryId() {
    return `entry-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
}

function setValue(id, value) {
    const element = document.getElementById(id);
    if (element) element.value = value;
}

function setChecked(id, value) {
    const element = document.getElementById(id);
    if (element) element.checked = Boolean(value);
}
