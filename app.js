const categories = {
  roof_state: "屋顶光伏（国企）",
  storage_charge: "光储充",
  carport: "光伏车棚",
  roof_private: "屋顶光伏（民企）",
};

const categoryShort = {
  roof_state: "国企光伏",
  storage_charge: "光储充",
  carport: "车棚",
  roof_private: "民企光伏",
};

const fieldDefs = [
  ["projectName", "项目信息", "wide"],
  ["projectCompany", "项目单位"],
  ["projectContact", "项目公司联系人"],
  ["projectPhone", "项目公司手机号"],
  ["mainCompany", "主体公司"],
  ["mainContact", "主体公司联系人"],
  ["mainPhone", "主体公司手机号"],
  ["mainAddress", "主体公司地址", "wide"],
  ["relationGraph", "关系图谱", "wide"],
  ["investor", "投资人"],
  ["projectSituation", "项目情况", "wide"],
  ["projectProgress", "项目进展", "wide"],
  ["projectLocation", "项目所在地", "wide"],
  ["recordCode", "项目备案编号"],
  ["remark", "备注", "wide"],
];

const metaFieldDefs = [
  ["source", "采集来源"],
  ["sourceId", "采集ID"],
  ["recordDate", "采集日期"],
];

const exportColumns = [
  ["projectName", "项目信息"],
  ["projectCompany", "项目单位"],
  ["category", "项目性质"],
  ["projectContact", "项目公司联系人"],
  ["projectPhone", "手机号"],
  ["mainCompany", "主体公司"],
  ["mainContact", "主体公司联系人"],
  ["mainPhone", "手机号"],
  ["mainAddress", "主体公司地址"],
  ["relationGraph", "关系图谱"],
  ["investor", "投资人"],
  ["projectSituation", "项目情况"],
  ["projectProgress", "项目进展"],
  ["projectLocation", "项目所在地"],
  ["recordCode", "项目备案编号"],
  ["remark", "备注"],
  ["projectSummary", "项目总结"],
  ["phoneFeedback", "电话反馈"],
];

const storageKey = "target-agent-platform-v1";
  const filingDefaultKeywords = "光伏 分布式光伏 屋顶 车棚 充电桩 充电 超充 光储充 储能 新能源 kW kWh";
const filingSourceName = "深圳投资项目公示";

function createClientId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  const random = Math.random().toString(16).slice(2);
  return `erp-${Date.now().toString(16)}-${random}`;
}

const demoProjects = [
  {
    id: createClientId(),
    category: "carport",
    projectName: "深圳宝安万科翡丽郡三期停车场充电站",
    projectCompany: "深圳利民通科技发展有限公司",
    projectContact: "程勇民",
    projectPhone: "13714077797",
    projectAddress: "深圳市龙华区龙华街道清湖社区清庆路1号",
    mainCompany: "深圳民思电科技发展有限公司",
    mainContact: "谭思燕",
    mainPhone: "13714077797",
    mainAddress: "深圳市龙华区观澜街道库坑社区",
    relationGraph: "探迹股权穿透图待接入",
    investor: "业主企业自投",
    projectSituation: "停车场充电站，直流快充桩与交流慢充桩组合。",
    projectProgress: "已备案，待电网接入与施工进场。",
    projectLocation: "广东省深圳市宝安区沙井街道",
    recordCode: "2605-440306-04-01-117059",
    remark: "探迹已取联系人和股权线索。",
    projectSummary: "",
    phoneFeedback: "",
    source: "样例",
    sourceId: "",
    recordDate: "",
    tungeeStatus: "已取信息",
    reviewStatus: "待人工审核",
    queued: false,
  },
  {
    id: createClientId(),
    category: "storage_charge",
    projectName: "低山南路吉桦厂储能电站项目",
    projectCompany: "安思能源(深圳)有限公司",
    projectContact: "刘建新",
    projectPhone: "13823283218",
    projectAddress: "深圳市龙岗区龙岗街道新生社区",
    mainCompany: "无",
    mainContact: "无",
    mainPhone: "无",
    mainAddress: "无",
    relationGraph: "探迹股权穿透图待接入",
    investor: "业主企业自投",
    projectSituation: "550kW/1120kWh 用户侧储能电站。",
    projectProgress: "已备案，处于前期设计或待建设阶段。",
    projectLocation: "广东省深圳市龙岗区龙岗街道",
    recordCode: "2509-440307-04-05-342153",
    remark: "同股东线索待复核。",
    projectSummary: "",
    phoneFeedback: "",
    source: "样例",
    sourceId: "",
    recordDate: "",
    tungeeStatus: "已取信息",
    reviewStatus: "待人工审核",
    queued: false,
  },
  {
    id: createClientId(),
    category: "roof_private",
    projectName: "深圳市启治科技有限公司190KW分布式光伏发电项目",
    projectCompany: "深圳市启治科技有限公司",
    projectContact: "周建治",
    projectPhone: "未查到",
    projectAddress: "深圳市龙岗区宝龙街道同乐社区",
    mainCompany: "无",
    mainContact: "无",
    mainPhone: "无",
    mainAddress: "无",
    relationGraph: "",
    investor: "业主企业自投",
    projectSituation: "190KW 分布式光伏发电项目。",
    projectProgress: "已备案，待物业施工审批。",
    projectLocation: "深圳市宝安区航城街道",
    recordCode: "2603-440306-04-05-372961",
    remark: "",
    projectSummary: "",
    phoneFeedback: "",
    source: "样例",
    sourceId: "",
    recordDate: "",
    tungeeStatus: "待查探迹",
    reviewStatus: "待查探迹",
    queued: false,
  },
];

let state = loadState();
let selectedId = state.projects[0]?.id || null;
let activeCategory = "all";
let activeCustomerStage = "target";
let activeRecordDate = null;
let filingRows = [];
let filingRawRows = [];
let filingDisplayMode = "filtered";
let selectedFilingKeys = new Set();
let activeFilingJobId = "";
let filingPollTimer = null;
let detailOpen = false;
let projectSaveTimer = null;
const projectSaveStates = new Map();
let investigationCenter = { seats: [], tasks: [] };
let investigationCenterLoaded = false;
let investigationCenterPollTimer = null;
let queueFilter = "active";
let activeView = "workspace";
let currentUser = { name: "本机管理员", role: "admin", department: "all" };
let currentFilingJob = null;

const els = {
  loginGate: document.getElementById("loginGate"),
  loginForm: document.getElementById("loginForm"),
  usernameInput: document.getElementById("usernameInput"),
  accessCodeInput: document.getElementById("accessCodeInput"),
    loginError: document.getElementById("loginError"),
    currentUserName: document.getElementById("currentUserName"),
    currentUserRole: document.getElementById("currentUserRole"),
    logoutBtn: document.getElementById("logoutBtn"),
    topbarEyebrow: document.getElementById("topbarEyebrow"),
    topbarTitle: document.getElementById("topbarTitle"),
  navItems: document.querySelectorAll(".nav-item"),
  salesTabs: document.querySelectorAll(".sales-tab"),
  salesTabsPanel: document.getElementById("salesTabs"),
  views: document.querySelectorAll(".view"),
  csvInput: document.getElementById("csvInput"),
  loadCaitoubiaoBtn: document.getElementById("loadCaitoubiaoBtn"),
  loadDbBtn: document.getElementById("loadDbBtn"),
  dbStatus: document.getElementById("dbStatus"),
  projectHead: document.getElementById("projectHead"),
  addDemoBtn: document.getElementById("addDemoBtn"),
  clearBtn: document.getElementById("clearBtn"),
  projectRows: document.getElementById("projectRows"),
  projectCount: document.getElementById("projectCount"),
  resultDateFilter: document.getElementById("resultDateFilter"),
  resultDateCaption: document.getElementById("resultDateCaption"),
  metricScopeLabel: document.getElementById("metricScopeLabel"),
  tableExportBtn: document.getElementById("tableExportBtn"),
  workflowBanner: document.getElementById("workflowBanner"),
  detailPanel: document.getElementById("detailPanel"),
  detailBackdrop: document.getElementById("detailBackdrop"),
  filingDateInput: document.getElementById("filingDateInput"),
  filingKeywordsInput: document.getElementById("filingKeywordsInput"),
  searchFilingBtn: document.getElementById("searchFilingBtn"),
  refreshFilingBtn: document.getElementById("refreshFilingBtn"),
  filterFilingBtn: document.getElementById("filterFilingBtn"),
  filingStatus: document.getElementById("filingStatus"),
  filingJobCard: document.getElementById("filingJobCard"),
  filingJobTitle: document.getElementById("filingJobTitle"),
  filingJobBadge: document.getElementById("filingJobBadge"),
  filingJobTimeline: document.getElementById("filingJobTimeline"),
  filingJobMeta: document.getElementById("filingJobMeta"),
  filingRows: document.getElementById("filingRows"),
  showFilteredFilingsBtn: document.getElementById("showFilteredFilingsBtn"),
  showRawFilingsBtn: document.getElementById("showRawFilingsBtn"),
  selectAllFilings: document.getElementById("selectAllFilings"),
  addSelectedFilingsBtn: document.getElementById("addSelectedFilingsBtn"),
  searchInput: document.getElementById("searchInput"),
  queueSelectedBtn: document.getElementById("queueSelectedBtn"),
  segments: document.querySelectorAll("[data-category]"),
  customerStages: document.querySelectorAll(".customer-stage"),
  seatSummary: document.getElementById("seatSummary"),
  seatList: document.getElementById("seatList"),
  centerStatus: document.getElementById("centerStatus"),
  addSeatBtn: document.getElementById("addSeatBtn"),
  queueList: document.getElementById("queueList"),
  queueFilters: document.getElementById("queueFilters"),
  doubaoLoginBtn: document.getElementById("doubaoLoginBtn"),
  startInvestigationBtn: document.getElementById("startInvestigationBtn"),
  sheetCounts: document.getElementById("sheetCounts"),
  exportCsvBtn: document.getElementById("exportCsvBtn"),
  copyJsonBtn: document.getElementById("copyJsonBtn"),
  exportPreview: document.getElementById("exportPreview"),
};

if (els.filterFilingBtn) els.filterFilingBtn.disabled = true;

function defaultState() {
  return {
    projects: [],
    seats: [
      { id: createClientId(), name: "探迹席位 A", status: "空闲", todayCount: 0 },
      { id: createClientId(), name: "探迹席位 B", status: "空闲", todayCount: 0 },
    ],
  };
}

function loadState() {
  const raw = localStorage.getItem(storageKey);
  if (!raw) return defaultState();
  try {
    const parsed = JSON.parse(raw);
    return {
      projects: Array.isArray(parsed.projects) ? parsed.projects : [],
      seats: Array.isArray(parsed.seats) ? parsed.seats : defaultState().seats,
    };
  } catch {
    return defaultState();
  }
}

function saveState() {
  // MySQL is authoritative. Persist only unsaved local imports so a wide
  // 417-row dataset is not serialized on every render in employee browsers.
  localStorage.setItem(storageKey, JSON.stringify({
    projects: state.projects.filter((project) => !project.dbId),
    seats: state.seats,
  }));
}

function normalizeProject(row) {
  const get = (...names) => {
    for (const name of names) {
      if (row[name] !== undefined && row[name] !== "") return row[name];
    }
    return "";
  };
  const projectName = get("项目信息", "项目名称", "projectName", "name");
  const company = get("项目单位", "备案公司", "projectCompany", "company");
  return {
    id: createClientId(),
    category: guessCategory(projectName),
    source: get("来源", "source") || "CSV导入",
    sourceId: get("采集ID", "project_id", "id"),
    recordDate: get("采集日期", "record_date", "recordDate"),
    projectName,
    projectCompany: company,
    projectContact: get("项目公司联系人", "联系人"),
    projectPhone: get("手机号", "项目公司手机号", "电话"),
    projectAddress: get("地址", "项目公司地址"),
    mainCompany: get("主体公司"),
    mainContact: get("主体公司联系人"),
    mainPhone: get("主体公司手机号", "主体手机号", "主体公司手机", "主手机号"),
    mainAddress: get("主体公司地址"),
    relationGraph: get("关系图谱"),
    investor: get("投资人"),
    projectSituation: get("项目情况"),
    projectProgress: get("项目进展"),
    projectLocation: get("项目所在地"),
    recordCode: get("项目备案编号", "备案编号"),
    remark: get("备注"),
    projectSummary: get("项目总结"),
    phoneFeedback: get("电话反馈"),
    tungeeStatus: "待查探迹",
    reviewStatus: "待查探迹",
    queued: false,
  };
}

function normalizeCaitoubiaoProject(row) {
  const projectName = row.company_name || "";
  return {
    id: createClientId(),
    category: guessCategory(projectName),
    source: "采投标",
    sourceId: row.project_id || "",
    recordDate: row.record_date || "",
    projectName,
    projectCompany: row.project_unit || "",
    projectContact: "",
    projectPhone: "",
    projectAddress: "",
    mainCompany: "",
    mainContact: "",
    mainPhone: "",
    mainAddress: "",
    relationGraph: "",
    investor: "",
    projectSituation: "",
    projectProgress: "",
    projectLocation: "",
    recordCode: row.credit_code || "",
    remark: row.project_id ? `采投标项目ID：${row.project_id}` : "",
    projectSummary: "",
    phoneFeedback: "",
    tungeeStatus: "待查探迹",
    reviewStatus: "待查探迹",
    queued: true,
  };
}

function normalizeFilingProject(row) {
  const projectName = row.projectName || "";
  const sourceId = row.sourceId || row.projectCode || "";
  return {
    id: createClientId(),
    category: guessCategory(`${projectName} ${row.projectUnit || ""}`),
    source: row.source || filingSourceName,
    sourceId,
    recordDate: row.recordDate || "",
    projectName,
    projectCompany: row.projectUnit || "",
    projectContact: "",
    projectPhone: "",
    projectAddress: "",
    mainCompany: "",
    mainContact: "",
    mainPhone: "",
    mainAddress: "",
    relationGraph: "",
    investor: "",
    projectSituation: "",
    projectProgress: row.projectType || "",
    projectLocation: "",
    recordCode: row.projectCode || "",
    remark: row.sourceUrl ? `来源网址：${row.sourceUrl}` : "",
    projectSummary: "",
    phoneFeedback: "",
    tungeeStatus: "待查探迹",
    reviewStatus: "待查探迹",
    queued: true,
  };
}

function normalizeDbProject(row) {
  const item = { ...row };
  item.dbId = row.dbId || "";
  item.id = item.dbId ? `db-${item.dbId}` : row.id || row.sourceId || createClientId();
  const inferredCategory = guessCategory(`${row.projectName || ""} ${row.projectCompany || ""} ${row.mainCompany || ""}`);
  item.category = inferredCategory !== "roof_private" ? inferredCategory : row.category || inferredCategory;
  item.source = row.source || "MySQL";
  item.sourceId = row.sourceId || "";
  item.recordDate = row.recordDate || "";
  item.tungeeStatus = row.tungeeStatus || "已取信息";
  item.reviewStatus = row.reviewStatus || "待人工审核";
  item.queued = Boolean(row.queued);
  for (const [key] of [...exportColumns, ...metaFieldDefs]) {
    if (item[key] == null) item[key] = "";
  }
  return item;
}

function appendProjects(projects) {
  const existingKeys = new Set(state.projects.flatMap(projectIdentityKeys));
  const fresh = projects.filter((project) => {
    const keys = projectIdentityKeys(project);
    if (keys.some((key) => existingKeys.has(key))) return false;
    keys.forEach((key) => existingKeys.add(key));
    return true;
  });
  state.projects = [...state.projects, ...fresh];
  if (!selectedId && state.projects.length) selectedId = state.projects[0].id;
  return fresh.length;
}

function projectIdentityKeys(project) {
  const keys = [];
  const recordCode = String(project.recordCode || "").trim().toLowerCase();
  const sourceId = String(project.sourceId || "").trim().toLowerCase();
  const projectName = String(project.projectName || "").trim().toLowerCase();
  const projectCompany = String(project.projectCompany || "").trim().toLowerCase();
  if (recordCode) keys.push(`code|${recordCode}`);
  if (sourceId) keys.push(`id|${sourceId}`);
  if (projectName || projectCompany) keys.push(`name|${projectName}|${projectCompany}`);
  return keys;
}

function guessCategory(name) {
  const text = String(name || "");
  if (/储能|光储充|kwh|mwh|电池/i.test(text)) return "storage_charge";
  if (/车棚|停车场|充电站|超充|充电桩/i.test(text)) return "carport";
  if (/国企|华润|中建|中铁|城建|招商|深能|国电|华能|南网|国家电投/.test(text)) return "roof_state";
  return "roof_private";
}

function filteredProjects() {
  const keyword = els.searchInput.value.trim().toLowerCase();
  return state.projects.filter((project) => {
    const projectDate = String(project.recordDate || "").slice(0, 10);
    const matchDate = !activeRecordDate || (activeRecordDate === "__undated__" ? !projectDate : projectDate === activeRecordDate);
    const matchCategory = activeCategory === "all" || project.category === activeCategory;
    const isMet = /见面|拜访|面谈|到访/.test(String(project.phoneFeedback || ""));
    const matchStage = activeCustomerStage === "target" || isMet;
    const haystack = [...exportColumns.map(([key]) => project[key] || ""), project.source || "", project.sourceId || ""].join(" ").toLowerCase();
    return matchDate && matchCategory && matchStage && (!keyword || haystack.includes(keyword));
  });
}

function recordDateCounts() {
  const counts = new Map();
  let undated = 0;
  for (const project of state.projects) {
    const date = String(project.recordDate || "").slice(0, 10);
    if (date) counts.set(date, (counts.get(date) || 0) + 1);
    else undated += 1;
  }
  return { dates: [...counts.entries()].sort(([left], [right]) => right.localeCompare(left)), undated };
}

function renderDateFilter() {
  const { dates, undated } = recordDateCounts();
  const available = new Set([...dates.map(([date]) => date), ...(undated ? ["__undated__"] : [])]);
  if ((activeRecordDate === null && available.size) || (activeRecordDate && !available.has(activeRecordDate))) {
    activeRecordDate = dates[0]?.[0] || (undated ? "__undated__" : "");
  }
  els.resultDateFilter.innerHTML = [
    ...dates.map(([date, count]) => `<option value="${escapeHtml(date)}">${escapeHtml(date)}（${count}条）</option>`),
    ...(undated ? [`<option value="__undated__">未标日期（${undated}条）</option>`] : []),
    `<option value="">全部日期（${state.projects.length}条）</option>`,
  ].join("");
  els.resultDateFilter.value = activeRecordDate || "";
  const dateLabel = activeRecordDate === "__undated__" ? "未标日期" : activeRecordDate || "全部日期";
  els.resultDateCaption.textContent = `${dateLabel} · 客户转化跟踪 · ${exportColumns.length} 列`;
}

function render() {
  renderDateFilter();
  renderTableHead();
  renderMetrics();
  renderRows();
  renderFilingRows();
  renderDetail();
  renderSeats();
  renderQueue();
  renderWorkflowBanner();
  renderExport();
  saveState();
}

function showView(viewName) {
  activeView = viewName;
  if (investigationCenterPollTimer) {
    clearTimeout(investigationCenterPollTimer);
    investigationCenterPollTimer = null;
  }
  els.views.forEach((view) => view.classList.remove("is-visible"));
  document.getElementById(`view-${viewName}`).classList.add("is-visible");
  const inSales = ["filing", "workspace", "accounts", "export"].includes(viewName);
  document.querySelectorAll(".sales-only").forEach((element) => element.classList.toggle("department-hidden", !inSales));
  els.salesTabsPanel.classList.toggle("is-hidden", !inSales);
  els.salesTabs.forEach((tab) => tab.classList.toggle("is-active", tab.dataset.salesView === viewName));
  const departmentCopy = {
    business: ["商务部 · 独立工作区", "商务管理工作台"],
    admin: ["人事行政部 · 独立工作区", "人事行政工作台"],
  };
  const copy = departmentCopy[viewName] || ["电销部 · 光伏项目线索", "光伏项目销售线索"];
  els.topbarEyebrow.textContent = copy[0];
  els.topbarTitle.textContent = copy[1];
  if (viewName === "accounts") loadInvestigationCenter();
}

function initFilingSearch() {
  if (els.filingDateInput && !els.filingDateInput.value) {
    els.filingDateInput.value = todayIso();
  }
  if (els.filingKeywordsInput && !els.filingKeywordsInput.value) {
    els.filingKeywordsInput.value = filingDefaultKeywords;
  }
  renderFilingRows();
}

function todayIso() {
  const date = new Date();
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function renderFilingRows() {
  if (!els.filingRows) return;
  const displayRows = filingDisplayMode === "raw" ? filingRawRows : filingRows;
  if (!displayRows.length) {
    els.filingRows.innerHTML = '<tr><td colspan="6" class="empty-row">暂无备案项目</td></tr>';
    return;
  }
  els.filingRows.innerHTML = displayRows
    .map(
      (row, index) => `
      <tr data-index="${index}">
        <td class="check-col">
          <input class="filing-check" type="checkbox" data-index="${index}" ${selectedFilingKeys.has(filingRowKey(row)) ? "checked" : ""} />
        </td>
        <td title="${escapeHtml(row.projectCode || "")}">${escapeHtml(row.projectCode || "")}</td>
        <td title="${escapeHtml(row.projectName || "")}"><div class="filing-name">${escapeHtml(row.projectName || "")}</div></td>
        <td title="${escapeHtml(row.projectUnit || "")}">${escapeHtml(row.projectUnit || "")}</td>
        <td>${escapeHtml(row.projectType || "")}</td>
        <td>${escapeHtml(row.recordDate || "")}</td>
      </tr>
    `,
    )
    .join("");
  updateFilingSelectionUi();
}

function filingRowKey(row) {
  return String(row?.sourceId || row?.projectCode || `${row?.recordDate || ""}|${row?.projectUnit || ""}|${row?.projectName || ""}`);
}

function currentFilingDisplayRows() {
  return filingDisplayMode === "raw" ? filingRawRows : filingRows;
}

function updateFilingSelectionUi() {
  const displayRows = currentFilingDisplayRows();
  const selectedCount = filingRawRows.filter((row) => selectedFilingKeys.has(filingRowKey(row))).length;
  const allVisibleSelected = displayRows.length > 0 && displayRows.every((row) => selectedFilingKeys.has(filingRowKey(row)));
  els.selectAllFilings.checked = allVisibleSelected;
  els.selectAllFilings.indeterminate = !allVisibleSelected && displayRows.some((row) => selectedFilingKeys.has(filingRowKey(row)));
  els.addSelectedFilingsBtn.disabled = selectedCount === 0;
  els.addSelectedFilingsBtn.textContent = `3　加入项目线索并开始调查（${selectedCount}条）`;
}

function normalizeFilingKeyword(value) {
  return String(value || "")
    .toLowerCase()
    .replaceAll("千瓦时", "kwh")
    .replaceAll("千瓦", "kw")
    .replace(/[\s_\-_/·•]+/g, "");
}

function filterFilingRows(rows, keywordText) {
  const keywords = String(keywordText || "")
    .split(/[\s,，、]+/)
    .map(normalizeFilingKeyword)
    .filter(Boolean);
  if (!keywords.length) return [...rows];
  return rows.filter((row) => {
    const haystack = normalizeFilingKeyword(
      [row.projectName, row.projectUnit, row.projectType].filter(Boolean).join(" "),
    );
    return keywords.some((keyword) => haystack.includes(keyword));
  });
}

function renderFilingJob(job = currentFilingJob) {
  currentFilingJob = job || null;
  if (!job || !els.filingJobCard) {
    if (els.filingJobCard) els.filingJobCard.hidden = true;
    return;
  }
  els.filingJobCard.hidden = false;
  const statusLabels = { queued: "排队中", running: "采集中", done: "采集完成", failed: "采集失败" };
  els.filingJobTitle.textContent = `${job.date || ""} · 任务 ${job.id || ""}`;
  els.filingJobBadge.textContent = statusLabels[job.status] || job.status || "等待";
  els.filingJobBadge.className = `task-status ${job.status || ""}`;
  const stages = [
    ["提交查询", Boolean(job.createdAt), job.createdAt || ""],
    ["读取/采集备案", ["running", "done", "failed"].includes(job.status), job.startedAt || "等待开始"],
    ["原始数据就绪", job.status === "done", job.status === "done" ? `${job.totalCount ?? job.count ?? 0} 条，可继续筛选` : "等待采集"],
  ];
  els.filingJobTimeline.innerHTML = stages.map(([label, active, note], index) => `
    <div class="job-stage ${active ? "is-done" : ""}">
      <span class="stage-index">${index + 1}</span>
      <div><strong>${escapeHtml(label)}</strong><span>${escapeHtml(note)}</span></div>
    </div>`).join("");
  const mode = job.readMode === "live_crawler" ? "实时采集" : job.readMode === "filing_database" ? "数据库读取" : job.readMode ? "缓存读取" : "等待判断";
  els.filingJobMeta.textContent = `创建：${job.createdAt || "-"} · 开始：${job.startedAt || "-"} · 完成：${job.finishedAt || "-"} · 方式：${mode}`;
}

async function loadRecentFilingJob() {
  try {
    const response = await fetch("/api/filing-jobs?recent=1&limit=1", { cache: "no-store" });
    const payload = await response.json();
    if (payload.ok && payload.jobs?.length) renderFilingJob(payload.jobs[0]);
  } catch (_) {
    // History is supplementary; filing search remains usable without it.
  }
}

function renderTableHead() {
  els.projectHead.innerHTML = exportColumns.map(([key, label]) => `<th class="${columnClass(key)}">${escapeHtml(label)}</th>`).join("");
}

function renderMetrics() {
  const dateProjects = state.projects.filter((project) => {
    const projectDate = String(project.recordDate || "").slice(0, 10);
    return !activeRecordDate || (activeRecordDate === "__undated__" ? !projectDate : projectDate === activeRecordDate);
  });
  const pending = dateProjects.filter((p) => !p.phoneFeedback && (p.projectPhone || p.mainPhone)).length;
  const collected = dateProjects.length;
  const review = dateProjects.filter((p) => Boolean(p.phoneFeedback)).length;
  const exportable = dateProjects.filter((p) => p.mainCompany && (p.projectPhone || p.mainPhone)).length;
  els.metricScopeLabel.textContent = activeRecordDate ? "所选日期项目" : "全部项目";
  document.getElementById("metricPending").textContent = pending;
  document.getElementById("metricCollected").textContent = collected;
  document.getElementById("metricReview").textContent = review;
  document.getElementById("metricExportable").textContent = exportable;
  document.getElementById("todayTarget").textContent = `${review} / ${Math.max(30, state.projects.length)}`;
  document.getElementById("targetMeter").style.width = `${Math.min(100, (review / Math.max(30, state.projects.length)) * 100)}%`;
}

function renderWorkflowBanner() {
  if (!els.workflowBanner) return;
  if (!investigationCenterLoaded) {
    els.workflowBanner.innerHTML = "<strong>今日项目线索</strong><span>后台自动处理服务运行中</span>";
    return;
  }
  const tasks = investigationCenter.tasks;
  const processing = tasks.filter((task) => ["doubao_queued", "doubao_running", "tungee_queued", "running", "research_running"].includes(task.status)).length;
  const completed = tasks.filter((task) => task.status === "completed").length;
  const review = state.projects.filter((project) => project.reviewStatus === "待人工审核").length;
  const failed = tasks.filter((task) => ["failed", "research_failed"].includes(task.status)).length;
  els.workflowBanner.innerHTML = `<strong>今日项目线索</strong><span>处理中 ${processing} 条 · 已生成线索 ${completed} 条 · 待人工审核 ${review} 条${failed ? ` · 异常 ${failed} 条` : ""}</span>`;
}

function renderRows() {
  const rows = filteredProjects();
  els.projectCount.textContent = `${rows.length} 条`;
  els.queueSelectedBtn.disabled = !selectedId;
  els.projectRows.innerHTML = rows
    .map(
      (project, index) => `
      <tr class="${project.id === selectedId ? "is-selected" : ""}" data-id="${project.id}" tabindex="0" title="点击编辑此项目">
        ${exportColumns.map(([key]) => renderTableCell(project, key, index)).join("")}
      </tr>
    `,
    )
    .join("");
}

function readableEquity(value) {
  const text = String(value || "").trim();
  if (!text || !text.startsWith("{")) return text;
  try {
    const parsed = JSON.parse(text);
    const chain = parsed.project_company ? parsed : parsed.股权穿透 || parsed;
    const lines = [];
    const projectCompany = chain.project_company?.company_name;
    const shareholder = chain.direct_shareholder || {};
    const controlling = chain.controlling_company || {};
    if (projectCompany) lines.push(`备案项目单位：${projectCompany}`);
    if (shareholder.name) lines.push(`一级股东：${shareholder.name}${shareholder.ratio !== undefined ? `（持股 ${shareholder.ratio}%）` : ""}`);
    if (controlling.company_name) lines.push(`背后控股公司：${controlling.company_name}`);
    if (controlling.legal_representative || controlling.contact_person) lines.push(`关键决策人：${controlling.legal_representative || controlling.contact_person}`);
    if (chain.最终控股方) lines.push(`最终控股方：${chain.最终控股方}`);
    if (chain.实际控制人) lines.push(`实际控制人：${chain.实际控制人}`);
    return lines.length ? `${lines.join("；")}。以上结果需结合工商详情人工复核。` : text;
  } catch (_) {
    return text;
  }
}

function renderTableCell(project, key, index = 0) {
  if (key === "sequence") {
    return `<td class="${columnClass(key)}"><div class="cell-text">${index + 1}</div></td>`;
  }
  const displayValue = key === "relationGraph"
    ? readableEquity(project[key])
    : key === "category" ? categories[project.category] || project.category || "待分类"
    : key === "projectLocation" && !project[key] ? "待确认" : project[key] || "";
  const value = escapeHtml(displayValue);
  const title = escapeHtml(displayValue);
  if ((key === "projectPhone" || key === "mainPhone") && project[key]) {
    const phone = String(project[key]).replace(/[^0-9+]/g, "");
    return `<td class="${columnClass(key)}" title="${title}"><a class="phone-link" href="tel:${escapeHtml(phone)}">${value}</a></td>`;
  }
  if (key === "projectName") {
    return `
      <td class="${columnClass(key)}" title="${title}">
        <div class="project-cell">
          <div class="cell-text project-title">${value || "未命名项目"}</div>
          <div class="cell-badges">
            <span class="source-pill">${escapeHtml(project.source || "手动")}</span>
            <span class="category-pill">${categoryShort[project.category] || "待分类"}</span>
          </div>
        </div>
      </td>
    `;
  }
  return `<td class="${columnClass(key)}" title="${title}"><div class="cell-text">${value}</div></td>`;
}

function columnClass(key) {
  const classes = [`col-${key}`];
  if (key === "recordDate") classes.push("sticky-col", "sticky-date");
  if (key === "sequence") classes.push("sticky-col", "sticky-sequence");
  if (isLongField(key)) classes.push("long-cell");
  return classes.join(" ");
}

function isLongField(key) {
  return ["relationGraph", "projectSituation", "projectProgress", "remark", "projectSummary", "phoneFeedback"].includes(key);
}

function renderDetail() {
  const project = state.projects.find((item) => item.id === selectedId);
  const isVisible = Boolean(project && detailOpen);
  els.detailPanel.classList.toggle("is-open", isVisible);
  els.detailBackdrop.classList.toggle("is-open", isVisible);
  document.body.classList.toggle("detail-is-open", isVisible);
  if (!isVisible) {
    els.detailPanel.innerHTML = "";
    return;
  }
  const template = document.getElementById("detailTemplate");
  const node = template.content.cloneNode(true);
  node.querySelector("[data-detail-title]").textContent = project.projectName || "未命名项目";
  applyProjectSaveStatus(node.querySelector("[data-save-status]"), project);

  const categorySelect = node.querySelector('[data-field="category"]');
  categorySelect.innerHTML = Object.entries(categories)
    .map(([value, label]) => `<option value="${value}">${label}</option>`)
    .join("");

  node.querySelectorAll(".detail-head [data-field]").forEach((input) => {
    const field = input.dataset.field;
    input.value = project[field] || "";
    input.addEventListener("input", () => {
      project[field] = input.value;
      if (field === "reviewStatus") project.tungeeStatus = input.value === "待查探迹" ? "待查探迹" : project.tungeeStatus;
      saveState();
      renderMetrics();
      renderRows();
      renderQueue();
      renderExport();
      queueProjectSave(project);
    });
  });

  const grid = node.querySelector(".field-grid");
  grid.innerHTML = fieldDefs
    .map(([field, label, mode]) => {
      const value = escapeHtml(field === "relationGraph" ? readableEquity(project[field]) : project[field] || "");
      const control =
        mode === "wide"
          ? `<textarea data-edit="${field}" ${currentUser.role === "admin" ? "" : "readonly"}>${value}</textarea>`
          : `<input data-edit="${field}" value="${value}" ${currentUser.role === "admin" ? "" : "readonly"}>`;
      return `<div class="field ${mode === "wide" ? "wide" : ""}"><label><span>${label}</span>${control}</label></div>`;
    })
    .join("");

  grid.querySelectorAll("[data-edit]").forEach((input) => {
    input.addEventListener("input", () => {
      project[input.dataset.edit] = input.value;
      saveState();
      renderMetrics();
      renderExport();
      queueProjectSave(project);
    });
  });

  const metaGrid = node.querySelector(".meta-grid");
  metaGrid.innerHTML = metaFieldDefs
    .map(([field, label]) => {
      const value = escapeHtml(project[field] || "");
      return `<div class="field"><label><span>${label}</span><input data-edit="${field}" value="${value}" readonly></label></div>`;
    })
    .join("");

  metaGrid.querySelectorAll("[data-edit]").forEach((input) => {
    input.addEventListener("input", () => {
      project[input.dataset.edit] = input.value;
      saveState();
      renderRows();
      queueProjectSave(project);
    });
  });

  node.querySelectorAll(".manual-row [data-field]").forEach((input) => {
    const field = input.dataset.field;
    input.value = project[field] || "";
    input.addEventListener("input", () => {
      project[field] = input.value;
      saveState();
      renderMetrics();
      renderExport();
      queueProjectSave(project);
    });
  });

  els.detailPanel.innerHTML = "";
  els.detailPanel.appendChild(node);
}

function applyProjectSaveStatus(element, project) {
  if (!element) return;
  const stateItem = projectSaveStates.get(project.id) || {
    label: project.dbId ? "已保存" : "尚未入库",
    tone: project.dbId ? "saved" : "",
  };
  element.textContent = stateItem.label;
  element.className = `save-status${stateItem.tone ? ` is-${stateItem.tone}` : ""}`;
}

function setProjectSaveStatus(project, label, tone = "") {
  projectSaveStates.set(project.id, { label, tone });
  const current = state.projects.find((item) => item.id === selectedId);
  if (detailOpen && current?.id === project.id) {
    applyProjectSaveStatus(els.detailPanel.querySelector("[data-save-status]"), project);
  }
}

function queueProjectSave(project) {
  if (!project.dbId) {
    setProjectSaveStatus(project, "尚未入库");
    return;
  }
  setProjectSaveStatus(project, "等待保存", "saving");
  if (projectSaveTimer) clearTimeout(projectSaveTimer);
  projectSaveTimer = setTimeout(() => persistProject(project), 650);
}

async function persistProject(project) {
  setProjectSaveStatus(project, "保存中", "saving");
  try {
    const response = await fetch("/api/leads/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project }),
    });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "保存失败");
    const savedTime = String(payload.savedAt || "").slice(11, 19);
    setProjectSaveStatus(project, savedTime ? `已保存 ${savedTime}` : "已保存", "saved");
  } catch (error) {
    setProjectSaveStatus(project, `保存失败：${error.message}`, "error");
  }
}

function closeDetail() {
  detailOpen = false;
  renderDetail();
  renderRows();
}

function renderSeats() {
  if (!investigationCenterLoaded) {
    els.seatSummary.innerHTML = "";
    els.seatList.innerHTML = '<div class="empty-row">正在读取服务器席位...</div>';
    return;
  }
  const stateLabels = { idle: "空闲", busy: "执行中", offline: "离线" };
  const statusLabels = { active: "已启用", disabled: "已停用" };
  const enabledSeats = investigationCenter.seats.filter((seat) => seat.status === "active");
  const disabledCount = investigationCenter.seats.length - enabledSeats.length;
  const idle = enabledSeats.filter((seat) => seat.state === "idle").length;
  const busy = enabledSeats.filter((seat) => seat.state === "busy").length;
  const today = enabledSeats.reduce((sum, seat) => sum + Number(seat.todayCount || 0), 0);
  els.seatSummary.innerHTML = `
    <div class="seat-metric"><strong>${enabledSeats.length}</strong><span>已启用${disabledCount ? ` · ${disabledCount} 个停用` : ""}</span></div>
    <div class="seat-metric"><strong>${idle}</strong><span>可用</span></div>
    <div class="seat-metric"><strong>${busy}</strong><span>探迹执行中</span></div>
    <div class="seat-metric"><strong>${today}</strong><span>今日已查</span></div>
  `;
  els.seatList.innerHTML = investigationCenter.seats
    .map(
      (seat) => {
        const currentTask = investigationCenter.tasks.find(
          (task) => String(task.assignedSeatId || "") === String(seat.id) && task.status === "running",
        );
        const currentTaskHtml = currentTask
          ? `<div class="seat-current"><span>当前任务 #${escapeHtml(currentTask.id)}</span><strong>${escapeHtml(currentTask.companyName || currentTask.projectName || "待确认企业")}</strong></div>`
          : seat.status === "active"
            ? `<div class="seat-current is-idle"><span>${seat.state === "busy" ? "任务状态同步中" : "等待下一条探迹任务"}</span></div>`
            : '<div class="seat-current is-offline"><span>登录验证后才会参与自动分流</span></div>';
        return `
      <article class="seat ${seat.status !== "active" ? "is-disabled" : ""}">
        <div class="seat-main">
          <div class="seat-heading">
            <strong>${escapeHtml(seat.name)}</strong>
            <span class="seat-badge ${escapeHtml(seat.state)}">${stateLabels[seat.state] || seat.state}</span>
            <span class="seat-status">${statusLabels[seat.status] || seat.status}</span>
          </div>
          <div class="seat-meta">
            <span>今日查询 <b>${seat.todayCount || 0}</b> 条</span>
            <span>最近使用 ${escapeHtml(seat.lastUsedAt || "暂无")}</span>
            <span>会话 ${escapeHtml(seat.profileKey || "未配置")}</span>
          </div>
          ${currentTaskHtml}
          ${seat.lastError ? `<div class="seat-error">${escapeHtml(seat.lastError)}</div>` : ""}
        </div>
        <div class="seat-actions">
          <button class="small-button login-seat" data-id="${seat.id}" ${seat.state === "busy" ? "disabled" : ""}>${seat.status === "active" ? "检查登录" : "登录并启用"}</button>
          ${seat.status === "active" ? `<button class="small-button toggle-seat" data-id="${seat.id}" ${seat.state === "busy" ? "disabled" : ""}>停用席位</button>` : ""}
        </div>
      </article>
    `;
      },
    )
    .join("") || '<div class="empty-row">暂无探迹席位</div>';
}

function renderQueue() {
  if (!investigationCenterLoaded) {
    els.queueList.innerHTML = "<li>正在读取服务器队列...</li>";
    return;
  }
  const statusLabels = {
    doubao_queued: "待豆包识别主体",
    doubao_running: "豆包识别主体中",
    tungee_queued: "待探迹查询主体",
    queued: "待分配",
    running: "探迹查询主体中",
    tungee_done: "探迹完成 · 待入库",
    research_running: "豆包调查中",
    research_failed: "综合调查失败 · 可重试",
    completed: "已完成",
    failed: "探迹失败",
    superseded: "历史失败已修复",
    cancelled: "已合并",
  };
  const groups = {
    active: new Set(["running", "doubao_running", "research_running"]),
    waiting: new Set(["queued", "doubao_queued", "tungee_queued", "tungee_done"]),
    failed: new Set(["failed", "research_failed"]),
    done: new Set(["completed", "superseded", "cancelled"]),
  };
  const counts = Object.fromEntries(
    Object.entries(groups).map(([key, statuses]) => [
      key,
      investigationCenter.tasks.filter((task) => statuses.has(task.status)).length,
    ]),
  );
  els.queueFilters?.querySelectorAll("[data-queue-filter]").forEach((button) => {
    const key = button.dataset.queueFilter;
    button.classList.toggle("is-active", key === queueFilter);
    const count = button.querySelector("b");
    if (count) count.textContent = counts[key] || 0;
  });
  const queueTasks = investigationCenter.tasks.filter((task) => groups[queueFilter]?.has(task.status));
  els.queueList.innerHTML = queueTasks
    .map(
      (task) => `<li class="task-row">
        <div class="task-heading">
          <span class="task-id">#${escapeHtml(task.id)}</span>
          <strong>${escapeHtml(task.companyName || task.projectName || `任务 ${task.id}`)}</strong>
          <span class="task-status ${escapeHtml(task.status)}">${statusLabels[task.status] || task.status}</span>
        </div>
        <span class="task-meta">${task.projectName && task.projectName !== task.companyName ? escapeHtml(task.projectName) : "备案项目"} · ${task.assignedSeatName ? `席位：${escapeHtml(task.assignedSeatName)}` : "等待分配"} · ${escapeHtml(task.platforms || "")}</span>
        <span class="task-time">创建于 ${escapeHtml(task.createdAt || "暂无")}${task.startedAt ? ` · 开始于 ${escapeHtml(task.startedAt)}` : ""}</span>
        ${task.error ? `<span class="${["cancelled", "superseded"].includes(task.status) ? "task-note" : "task-error"}">${escapeHtml(task.error)}</span>` : ""}
        ${["failed", "research_failed"].includes(task.status) ? `<button class="text-button internal-only retry-task" data-task-id="${escapeHtml(task.id)}" type="button">重试任务</button>` : ""}
      </li>`,
    )
    .join("") || `<li class="queue-empty">当前没有${queueFilter === "active" ? "进行中" : queueFilter === "waiting" ? "待处理" : queueFilter === "failed" ? "失败" : "已完成"}任务</li>`;
}

els.queueFilters?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-queue-filter]");
  if (!button) return;
  queueFilter = button.dataset.queueFilter || "active";
  renderQueue();
});

els.queueList.addEventListener("click", async (event) => {
  const button = event.target.closest(".retry-task");
  if (!button) return;
  button.disabled = true;
  try {
    const response = await fetch("/api/investigation-tasks/retry", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ taskId: button.dataset.taskId }),
    });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "任务重试失败");
    applyInvestigationCenter(payload);
    els.centerStatus.textContent = `任务 #${button.dataset.taskId} 已重新排队`;
  } catch (error) {
    els.centerStatus.textContent = `任务重试失败：${error.message}`;
    button.disabled = false;
  }
});

function applyInvestigationCenter(payload) {
  investigationCenter = {
    seats: Array.isArray(payload.seats) ? payload.seats : investigationCenter.seats,
    tasks: Array.isArray(payload.tasks) ? payload.tasks : investigationCenter.tasks,
  };
  investigationCenterLoaded = true;
  const activeSeats = investigationCenter.seats.filter((seat) => seat.status === "active").length;
  const tungeeRunning = investigationCenter.tasks.filter((task) => task.status === "running").length;
  const doubaoRunning = investigationCenter.tasks.filter((task) => ["doubao_running", "research_running"].includes(task.status)).length;
  const queued = investigationCenter.tasks.filter((task) => ["queued", "doubao_queued", "tungee_queued", "tungee_done"].includes(task.status)).length;
  els.centerStatus.textContent = `已启用席位 ${activeSeats} 个 · 探迹执行 ${tungeeRunning} · 豆包执行 ${doubaoRunning} · 待处理 ${queued}`;
  els.centerStatus.dataset.refreshedAt = String(Date.now());
  renderSeats();
  renderQueue();
  renderWorkflowBanner();
  renderFilingJob();
}

async function loadInvestigationCenter() {
  els.centerStatus.textContent = "正在连接服务器席位中心...";
  try {
    const response = await fetch("/api/investigation-center", { cache: "no-store" });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "席位中心读取失败");
    applyInvestigationCenter(payload);
  } catch (error) {
    investigationCenterLoaded = false;
    els.centerStatus.textContent = `席位中心不可用：${error.message}`;
    renderSeats();
    renderQueue();
  } finally {
    if (["workspace", "accounts"].includes(activeView)) {
      investigationCenterPollTimer = setTimeout(loadInvestigationCenter, 3000);
    }
  }
}

function renderExport() {
  const counts = Object.entries(categories).map(([key, label]) => {
    const count = state.projects.filter((project) => project.category === key).length;
    return `<div class="sheet-row"><span>${label}</span><strong>${count}</strong></div>`;
  });
  els.sheetCounts.innerHTML = counts.join("");
  els.exportPreview.value = activeView === "export" ? buildExportJson() : "";
}

function buildExportJson() {
  return JSON.stringify(
    {
      headers: exportColumns.map(([, label]) => label),
      rows: state.projects.map((project) => exportColumns.map(([key]) => project[key] || "")),
    },
    null,
    2,
  );
}

function statusClass(status) {
  if (status === "已取信息") return "collected";
  if (status === "待人工审核") return "review";
  if (status === "可导出") return "exportable";
  return "pending";
}

function toExportRow(project) {
  return exportColumns.map(([key]) => project[key] || "");
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];
    if (char === '"' && quoted && next === '"') {
      cell += '"';
      i += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      row.push(cell.trim());
      cell = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") i += 1;
      row.push(cell.trim());
      if (row.some(Boolean)) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }
  row.push(cell.trim());
  if (row.some(Boolean)) rows.push(row);
  const headers = rows.shift() || [];
  return rows.map((values) => Object.fromEntries(headers.map((header, index) => [header, values[index] || ""])));
}

function exportCsv() {
  const headers = exportColumns.map(([, label]) => label);
  const lines = [headers.join(",")];
  for (const project of state.projects) {
    lines.push(toExportRow(project).map((value) => csvCell(value)).join(","));
  }
  const blob = new Blob(["\ufeff" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `鑫众ERP系统_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

async function exportExcel(trigger = els.exportCsvBtn) {
  trigger.disabled = true;
  const originalText = trigger.textContent;
  trigger.textContent = "正在生成...";
  try {
    const query = activeRecordDate ? `?date=${encodeURIComponent(activeRecordDate)}` : "";
    const response = await fetch(`/api/export.xlsx${query}`);
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.error || "Excel 导出失败");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `鑫众ERP系统_${activeRecordDate || "全部日期"}.xlsx`;
    anchor.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    els.dbStatus.textContent = `导出失败：${error.message}`;
  } finally {
    trigger.disabled = false;
    trigger.textContent = originalText;
  }
}

function csvCell(value) {
  const text = String(value).replaceAll('"', '""');
  return /[",\n\r]/.test(text) ? `"${text}"` : text;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

els.navItems.forEach((item) => {
  item.addEventListener("click", () => {
    els.navItems.forEach((nav) => nav.classList.remove("is-active"));
    item.classList.add("is-active");
    showView(item.dataset.view);
  });
});

els.salesTabs.forEach((item) => {
  item.addEventListener("click", () => {
    els.navItems.forEach((nav) => nav.classList.toggle("is-active", nav.dataset.view === "filing"));
    showView(item.dataset.salesView);
  });
});

els.segments.forEach((item) => {
  if (item.classList.contains("customer-stage")) return;
  item.addEventListener("click", () => {
    els.segments.forEach((segment) => {
      if (!segment.classList.contains("customer-stage")) segment.classList.remove("is-active");
    });
    item.classList.add("is-active");
    activeCategory = item.dataset.category;
    renderRows();
  });
});

els.customerStages.forEach((item) => {
  item.addEventListener("click", () => {
    els.customerStages.forEach((segment) => segment.classList.remove("is-active"));
    item.classList.add("is-active");
    activeCustomerStage = item.dataset.stage || "target";
    selectedId = filteredProjects()[0]?.id || null;
    renderRows();
    renderDetail();
  });
});

els.projectRows.addEventListener("click", (event) => {
  const row = event.target.closest("tr[data-id]");
  if (!row) return;
  selectedId = row.dataset.id;
  detailOpen = true;
  render();
});

els.projectRows.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const row = event.target.closest("tr[data-id]");
  if (!row) return;
  event.preventDefault();
  selectedId = row.dataset.id;
  detailOpen = true;
  render();
});

els.detailPanel.addEventListener("click", (event) => {
  if (event.target.closest(".detail-close")) closeDetail();
});

els.detailBackdrop.addEventListener("click", closeDetail);

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && detailOpen) closeDetail();
});

els.searchInput.addEventListener("input", renderRows);

els.resultDateFilter.addEventListener("change", () => {
  activeRecordDate = els.resultDateFilter.value;
  selectedId = filteredProjects()[0]?.id || null;
  render();
});

els.queueSelectedBtn.addEventListener("click", async () => {
  const project = state.projects.find((item) => item.id === selectedId);
  if (!project?.dbId) {
    els.dbStatus.textContent = "请先把项目保存到数据库，再加入调查队列";
    return;
  }
  els.queueSelectedBtn.disabled = true;
  els.dbStatus.textContent = "正在加入服务器调查队列...";
  try {
    const response = await fetch("/api/investigation-tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ leadId: project.dbId, platforms: "探迹,豆包,百度" }),
    });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "加入调查队列失败");
    project.queued = true;
    applyInvestigationCenter(payload);
    renderRows();
    renderQueue();
    els.dbStatus.textContent = payload.duplicate ? "该项目已在调查队列中" : "项目已加入服务器调查队列";
  } catch (error) {
    els.dbStatus.textContent = `加入队列失败：${error.message}`;
  } finally {
    els.queueSelectedBtn.disabled = false;
  }
});

els.addDemoBtn.addEventListener("click", () => {
  appendProjects(demoProjects.map((project) => ({ ...project, id: createClientId() })));
  selectedId = state.projects[0]?.id || null;
  render();
});

els.loadCaitoubiaoBtn.addEventListener("click", () => {
  const seed = Array.isArray(window.caitoubiaoSeed) ? window.caitoubiaoSeed : [];
  const added = appendProjects(seed.map(normalizeCaitoubiaoProject));
  if (added > 0) selectedId = state.projects.find((project) => project.source === "采投标")?.id || selectedId;
  render();
});

els.clearBtn.addEventListener("click", () => {
  state.projects = [];
  selectedId = null;
  render();
});

async function loadDatabaseProjects() {
  els.dbStatus.textContent = "数据库：连接中...";
  try {
    const response = await fetch("/api/projects", { cache: "no-store" });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "数据库读取失败");
    state.projects = payload.projects
      .map(normalizeDbProject)
      .sort((left, right) => {
        const byDate = String(right.recordDate || "").localeCompare(String(left.recordDate || ""));
        if (byDate) return byDate;
        return Number(right.dbId || 0) - Number(left.dbId || 0);
      });
    selectedId = state.projects[0]?.id || null;
    els.dbStatus.textContent = `数据库：${payload.database}.${payload.table}，已读取 ${payload.count} 条`;
    render();
  } catch (error) {
    els.dbStatus.textContent = `数据库：未连接（${error.message}）`;
  }
}

els.loadDbBtn.addEventListener("click", loadDatabaseProjects);

  els.searchFilingBtn.addEventListener("click", searchFilings);
  els.refreshFilingBtn?.addEventListener("click", () => searchFilings(true));

els.filingKeywordsInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") searchFilings();
});

els.filingDateInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") searchFilings();
});

els.selectAllFilings.addEventListener("change", () => {
  currentFilingDisplayRows().forEach((row) => {
    const key = filingRowKey(row);
    if (els.selectAllFilings.checked) selectedFilingKeys.add(key);
    else selectedFilingKeys.delete(key);
  });
  renderFilingRows();
});

els.filingRows.addEventListener("change", (event) => {
  const checkbox = event.target.closest(".filing-check");
  if (!checkbox) return;
  const row = currentFilingDisplayRows()[Number(checkbox.dataset.index)];
  if (!row) return;
  const key = filingRowKey(row);
  if (checkbox.checked) selectedFilingKeys.add(key);
  else selectedFilingKeys.delete(key);
  updateFilingSelectionUi();
});

els.addSelectedFilingsBtn.addEventListener("click", addSelectedFilingsToLeads);

els.showFilteredFilingsBtn?.addEventListener("click", () => {
  filingDisplayMode = "filtered";
  els.showFilteredFilingsBtn.classList.add("is-active");
  els.showRawFilingsBtn.classList.remove("is-active");
  renderFilingRows();
});

els.showRawFilingsBtn?.addEventListener("click", () => {
  filingDisplayMode = "raw";
  els.showRawFilingsBtn.classList.add("is-active");
  els.showFilteredFilingsBtn.classList.remove("is-active");
  renderFilingRows();
});

els.filterFilingBtn?.addEventListener("click", () => {
  if (!filingRawRows.length) {
    els.filingStatus.textContent = "请先点击查询备案项目获取原始数据";
    return;
  }
  filingRows = filterFilingRows(filingRawRows, els.filingKeywordsInput.value);
  selectedFilingKeys = new Set(filingRows.map(filingRowKey));
  filingDisplayMode = "filtered";
  els.showFilteredFilingsBtn?.classList.add("is-active");
  els.showRawFilingsBtn?.classList.remove("is-active");
  els.selectAllFilings.checked = false;
  renderFilingRows();
  els.filingStatus.textContent = `关键词筛选完成：${filingRows.length} 条，已默认全选；确认后点击第 3 步加入项目线索并开始调查`;
});

async function searchFilings(forceRefresh = false) {
  const date = els.filingDateInput.value;
  const keywords = els.filingKeywordsInput.value.trim();
  if (!date) {
    els.filingStatus.textContent = "请选择立项日期";
    return;
  }
  if (filingPollTimer) clearTimeout(filingPollTimer);
  els.searchFilingBtn.disabled = true;
  if (els.filterFilingBtn) els.filterFilingBtn.disabled = true;
    els.filingStatus.textContent = "正在获取原始备案数据，不会启动公司调查...";
  try {
    const response = await fetch("/api/filing-jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date, keywords: "", forceRefresh: Boolean(forceRefresh) }),
    });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "采集任务提交失败");
    activeFilingJobId = payload.id;
      renderFilingJob(payload);
      els.filingStatus.textContent = `任务 ${payload.id} 已提交，服务器正在查询数据库或自动采集...`;
    pollFilingJob(payload.id);
  } catch (error) {
    filingRows = [];
    renderFilingRows();
    els.filingStatus.textContent = `查询失败：${error.message}`;
    els.searchFilingBtn.disabled = false;
  }
}

async function pollFilingJob(jobId) {
  try {
    const response = await fetch(`/api/filing-jobs?id=${encodeURIComponent(jobId)}`, { cache: "no-store" });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "读取任务状态失败");
    renderFilingJob(payload);

    if (payload.status === "queued" || payload.status === "running") {
      els.filingStatus.textContent = `任务 ${payload.id}：${payload.message || payload.status}`;
      filingPollTimer = setTimeout(() => pollFilingJob(jobId), 2000);
      return;
    }

    if (payload.status === "done") {
      filingRawRows = Array.isArray(payload.allRows)
        ? payload.allRows
        : Array.isArray(payload.rows) ? payload.rows : [];
      filingRows = [];
      selectedFilingKeys.clear();
      filingDisplayMode = "raw";
      els.showRawFilingsBtn?.classList.add("is-active");
      els.showFilteredFilingsBtn?.classList.remove("is-active");
      els.selectAllFilings.checked = false;
      renderFilingRows();
      const modeText = payload.readMode === "live_crawler"
        ? "实时采集"
        : payload.readMode === "filing_database"
          ? "数据库读取"
          : "缓存兜底";
      const errorHint = payload.crawlerError ? `（爬虫失败：${payload.crawlerError}）` : "";
        const totalHint = payload.totalCount ? `，原始数据 ${payload.totalCount} 条` : "";
        els.filingStatus.textContent = `备案获取完成：${payload.totalCount || filingRawRows.length} 条${totalHint}，来源：${payload.sourceLabel || "深圳投资项目公示"}，方式：${modeText}；请点击“关键词筛选”后再开始获取公司信息${errorHint}`;
      els.searchFilingBtn.disabled = false;
      els.filterFilingBtn.disabled = false;
      return;
    }

    throw new Error(payload.error || payload.message || "采集失败");
  } catch (error) {
    filingRows = [];
    filingRawRows = [];
    if (els.filterFilingBtn) els.filterFilingBtn.disabled = true;
    renderFilingRows();
    els.filingStatus.textContent = `任务失败：${error.message}`;
    els.searchFilingBtn.disabled = false;
  }
}

function selectedFilingRows() {
  return filingRawRows.filter((row) => selectedFilingKeys.has(filingRowKey(row)));
}

async function addSelectedFilingsToLeads() {
  const selected = selectedFilingRows();
  if (!selected.length) {
    els.filingStatus.textContent = "请先勾选备案项目";
    return;
  }
  const projects = selected.map(normalizeFilingProject);
  const submittedDate = String(selected[0]?.recordDate || "").slice(0, 10);
  els.addSelectedFilingsBtn.disabled = true;
  els.filingStatus.textContent = `正在保存 ${projects.length} 条备案项目到服务器数据库...`;
  try {
    const response = await fetch("/api/leads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ projects }),
    });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "备案项目保存失败");

    await loadDatabaseProjects();
    if (submittedDate) activeRecordDate = submittedDate;
    render();
    const queued = payload.queued || 0;
    const duplicates = payload.duplicates || 0;
    els.dbStatus.textContent = queued
      ? `已加入项目线索：新增 ${queued} 条，重复 ${duplicates} 条；新增项目已进入后台调查`
      : `${duplicates} 条均已存在，未重复创建；已打开 ${submittedDate || "对应日期"} 的项目线索`;
    selectedFilingKeys.clear();
    updateFilingSelectionUi();
    showView("workspace");
    loadInvestigationCenter();
  } catch (error) {
    els.filingStatus.textContent = `保存失败：${error.message}`;
  } finally {
    updateFilingSelectionUi();
  }
}

els.csvInput.addEventListener("change", async () => {
  const file = els.csvInput.files[0];
  if (!file) return;
  const text = await file.text();
  const imported = parseCsv(text).map(normalizeProject);
  state.projects = [...state.projects, ...imported];
  selectedId = state.projects[0]?.id || null;
  els.csvInput.value = "";
  render();
});

els.addSeatBtn.addEventListener("click", async () => {
  const confirmed = window.confirm("新增席位会创建一个默认停用的独立浏览器会话。创建后需完成探迹登录验证才会参与分流。确认新增吗？");
  if (!confirmed) return;
  els.addSeatBtn.disabled = true;
  try {
    const response = await fetch("/api/tungee-seats", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: `探迹席位 ${investigationCenter.seats.length + 1}` }),
    });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "新增席位失败");
    applyInvestigationCenter(payload);
  } catch (error) {
    els.centerStatus.textContent = `新增席位失败：${error.message}`;
  } finally {
    els.addSeatBtn.disabled = false;
  }
});

els.seatList.addEventListener("click", async (event) => {
  const loginBtn = event.target.closest(".login-seat");
  if (loginBtn) {
    loginBtn.disabled = true;
    try {
      const response = await fetch("/api/tungee-seats/open-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seatId: loginBtn.dataset.id }),
      });
      const payload = await response.json();
      if (!payload.ok) throw new Error(payload.error || "打开登录窗口失败");
      applyInvestigationCenter(payload);
      els.centerStatus.textContent = `${payload.message} 端口 ${payload.port}`;
    } catch (error) {
      els.centerStatus.textContent = `打开登录窗口失败：${error.message}`;
      loginBtn.disabled = false;
    }
    return;
  }
  const btn = event.target.closest(".toggle-seat");
  if (!btn) return;
  btn.disabled = true;
  try {
    const response = await fetch("/api/tungee-seats/toggle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seatId: btn.dataset.id }),
    });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "席位状态更新失败");
    applyInvestigationCenter(payload);
  } catch (error) {
    els.centerStatus.textContent = `席位操作失败：${error.message}`;
    btn.disabled = false;
  }
});

els.doubaoLoginBtn.addEventListener("click", async () => {
  els.doubaoLoginBtn.disabled = true;
  try {
    const response = await fetch("/api/research/open-doubao-login", { method: "POST" });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "打开豆包登录失败");
    applyInvestigationCenter(payload);
    els.centerStatus.textContent = `${payload.message} 端口 ${payload.port}`;
  } catch (error) {
    els.centerStatus.textContent = `打开豆包登录失败：${error.message}`;
  } finally {
    els.doubaoLoginBtn.disabled = false;
  }
});

els.startInvestigationBtn.addEventListener("click", async () => {
  els.startInvestigationBtn.disabled = true;
  els.centerStatus.textContent = "正在启动：豆包识别主体公司，完成后自动交给探迹...";
  try {
    const response = await fetch("/api/investigation-tasks/run-research-next", { method: "POST" });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "调查任务启动失败");
    applyInvestigationCenter(payload);
  } catch (error) {
    els.centerStatus.textContent = `调查任务启动失败：${error.message}`;
  } finally {
    els.startInvestigationBtn.disabled = false;
  }
});

els.tableExportBtn.addEventListener("click", () => exportExcel(els.tableExportBtn));
els.exportCsvBtn.addEventListener("click", () => exportExcel(els.exportCsvBtn));

els.copyJsonBtn.addEventListener("click", async () => {
  const value = els.exportPreview.value || buildExportJson();
  els.exportPreview.value = value;
  await navigator.clipboard.writeText(value);
});

async function ensureAuthenticated() {
  try {
    const response = await fetch("/api/session", { cache: "no-store" });
    const payload = await response.json();
    const allowed = !payload.authRequired || payload.authenticated;
    if (allowed && payload.user) {
      currentUser = payload.user;
      applyCurrentUser();
    }
    els.loginGate.hidden = allowed;
    return allowed;
  } catch (error) {
    els.loginGate.hidden = false;
    els.loginError.textContent = `无法连接服务器：${error.message}`;
    return false;
  }
}

async function bootstrap() {
  if (!(await ensureAuthenticated())) return;
  const salesAllowed = currentUser.role === "admin" || currentUser.department === "sales";
  if (salesAllowed) {
    initFilingSearch();
    showView("workspace");
    render();
    loadDatabaseProjects();
    loadRecentFilingJob();
  } else {
    const targetView = currentUser.department === "business" ? "business" : "admin";
    els.navItems.forEach((item) => item.classList.toggle("is-active", item.dataset.view === targetView));
    showView(targetView);
  }
}

els.loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  els.loginError.textContent = "正在登录...";
  try {
    const response = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: els.usernameInput.value, password: els.accessCodeInput.value }),
    });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "登录失败");
    els.accessCodeInput.value = "";
    currentUser = payload.user || currentUser;
    applyCurrentUser();
    els.loginError.textContent = "";
    await bootstrap();
  } catch (error) {
    els.loginError.textContent = error.message;
  }
});

function applyCurrentUser() {
  const roleLabels = { admin: "管理员", employee: "员工", manager: "部门主管" };
  const departmentLabels = { all: "全部部门", sales: "电销部", business: "商务部", hr: "人事行政部" };
  els.currentUserName.textContent = currentUser.name || currentUser.username || "内部用户";
  els.currentUserRole.textContent = `${departmentLabels[currentUser.department] || "内部"} · ${roleLabels[currentUser.role] || currentUser.role || "员工"}`;
  document.body.dataset.role = currentUser.role || "employee";
  document.body.dataset.department = currentUser.department || "sales";
  document.querySelectorAll(".internal-only").forEach((element) => {
    element.classList.toggle("role-hidden", currentUser.role !== "admin");
  });
  els.navItems.forEach((item) => {
    const view = item.dataset.view;
    const allowed = currentUser.role === "admin" ||
      (currentUser.department === "sales" && view === "filing") ||
      (currentUser.department === "business" && view === "business") ||
      (currentUser.department === "hr" && view === "admin");
    item.classList.toggle("role-hidden", !allowed);
  });
}

els.logoutBtn.addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST" });
  location.reload();
});

bootstrap();
