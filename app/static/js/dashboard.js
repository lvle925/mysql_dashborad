// 全局状态
let currentView = 'overview';
// Bootstrap 模态框实例
let detailsModal = null;

document.addEventListener('DOMContentLoaded', () => {
    console.log("Dashboard initialized");
    
    // 初始化 Bootstrap 模态框对象
    const modalEl = document.getElementById('detail-modal');
    if (modalEl) {
        detailsModal = new bootstrap.Modal(modalEl);
    }

    // 默认加载概览视图
    switchView('overview');
    
    // 启动自动刷新
    fetchAllData();
    setInterval(fetchAllData, 10000); // 10秒刷新一次
});

// --- 视图切换逻辑 ---
window.switchView = function(viewName) {
    console.log("Switching to view:", viewName);
    currentView = viewName;
    
    // 1. 菜单高亮
    document.querySelectorAll('.menu-item').forEach(el => {
        el.classList.remove('active');
        if(el.dataset.view === viewName) el.classList.add('active');
    });

    // 2. 内容面板切换
    document.querySelectorAll('.view-panel').forEach(el => {
        el.classList.remove('active');
        el.style.display = 'none';
    });
    
    const target = document.getElementById(`view-${viewName}`);
    if(target) {
        target.style.display = 'block';
        setTimeout(() => target.classList.add('active'), 10);
    }
    
    // 3. 动态标题更新 (已全部汉化)
    const titles = {
        'overview': '系统总览',
        'inference': '推理集群 (SGLang)',
        'database': '数据库拓扑 (MySQL)',
        'servers': '物理节点 (Zabbix)'
    };
    const titleEl = document.getElementById('page-title');
    if(titleEl) titleEl.innerText = titles[viewName] || '监控看板';
}

// --- 数据获取核心逻辑 ---
async function fetchAllData() {
    const btnIcon = document.querySelector('.btn-outline-primary i');
    if(btnIcon) btnIcon.classList.add('fa-spin');

    try {
        const res = await fetch('/api/data');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        
        updateLastTime(data.time);
        
        renderOverview(data);
        renderInference(data.inference);
        renderServers(data.servers);
        fetchReplErrors();
        
    } catch (e) {
        console.error("Fetch Error:", e);
    } finally {
        if(btnIcon) setTimeout(() => btnIcon.classList.remove('fa-spin'), 500);
    }
}

// 新增函数：获取并渲染跳过的错误
async function fetchReplErrors() {
    try {
        const res = await fetch('/api/repl/errors?hours=24');
        const data = await res.json();
        
        const container = document.getElementById('repl-errors-container');
        if (!container) return;

        if (data.count === 0) {
            container.innerHTML = `
                <div class="alert alert-success d-flex align-items-center">
                    <i class="fa-solid fa-check-circle me-2"></i>
                    <div>最近 24 小时无跳过的主从同步错误。</div>
                </div>`;
            return;
        }

        // 渲染错误表格
        let html = `
        <div class="card border-warning">
            <div class="card-header bg-warning text-dark fw-bold">
                <i class="fa-solid fa-triangle-exclamation me-2"></i> 
                检测到 ${data.count} 个跳过的同步错误 (最近24h)
            </div>
            <div class="table-responsive">
                <table class="table table-sm table-striped mb-0" style="font-size: 0.9rem;">
                    <thead>
                        <tr>
                            <th>时间</th>
                            <th>从库IP</th>
                            <th>错误码</th>
                            <th>Binlog位置</th>
                            <th>错误信息</th>
                        </tr>
                    </thead>
                    <tbody>`;
        
        data.errors.forEach(err => {
            html += `
            <tr>
                <td>${new Date(err.error_time).toLocaleString()}</td>
                <td class="font-monospace">${err.slave_ip}</td>
                <td><span class="badge bg-danger">${err.error_code}</span></td>
                <td class="font-monospace small">${err.master_log_file}:${err.master_log_pos}</td>
                <td class="text-wrap" style="max-width: 400px;">
                    <div class="text-truncate" title="${err.error_msg}">${err.error_msg}</div>
                </td>
            </tr>`;
        });

        html += `</tbody></table></div></div>`;
        container.innerHTML = html;

    } catch (e) {
        console.error("Fetch Repl Errors Failed:", e);
    }
}

function updateLastTime(time) {
    const el = document.getElementById('last-update');
    if(el) el.innerText = "更新于: " + time;
}

// --- 渲染概览 ---
function renderOverview(data) {
    const infCount = document.getElementById('stat-inf');
    if(infCount) infCount.innerText = data.inference.length;
    
    const srvCount = document.getElementById('stat-srv');
    if(srvCount) srvCount.innerText = Object.keys(data.servers).length;
    
    const alertCount = data.alerts.length;
    const alertEl = document.getElementById('stat-alert');
    if(alertEl) {
        alertEl.innerText = alertCount;
        alertEl.className = `fs-2 fw-bold ${alertCount > 0 ? 'text-danger' : 'text-success'}`;
    }

    const alertContainer = document.getElementById('overview-alerts');
    if (alertContainer) {
        if (alertCount === 0) {
            alertContainer.innerHTML = `
            <div class="alert alert-success d-flex align-items-center shadow-sm" role="alert">
                <i class="fa-solid fa-check-circle me-3 fs-4"></i>
                <div>
                    <strong>系统运行正常</strong>
                    <div class="small">所有监控指标均在正常范围内。</div>
                </div>
            </div>`;
        } else {
            alertContainer.innerHTML = data.alerts.map(a => `
                <div class="alert alert-${a.type==='crit'?'danger':'warning'} d-flex align-items-center shadow-sm mb-3" role="alert">
                    <i class="fa-solid fa-triangle-exclamation me-3 fs-4"></i>
                    <div>
                        <strong>${a.type==='crit'?'严重告警':'警告'}</strong>
                        <div class="small">${a.msg}</div>
                    </div>
                </div>
            `).join('');
        }
    }
}

// --- 渲染推理节点 ---
function renderInference(nodes) {
    const grid = document.getElementById('inf-grid');
    if (grid) {
        grid.innerHTML = nodes.map(n => {
            const isOk = n.status === 'ready';
            const borderClass = isOk ? 'border-success' : 'border-danger';
            const badgeClass = isOk ? 'bg-success' : 'bg-danger';
            const iconClass = isOk ? 'text-success' : 'text-danger';
            
            return `
            <div class="col">
                <div class="card h-100 shadow-sm border-top border-3 ${borderClass}">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <h6 class="card-title fw-bold m-0 text-dark">${n.name}</h6>
                            <i class="fa-solid fa-circle ${iconClass}" style="font-size:10px"></i>
                        </div>
                        <p class="card-text text-muted small font-monospace mb-3 bg-light p-1 rounded">
                            ${n.url}
                        </p>
                        
                        <div class="d-flex justify-content-between align-items-center border-top pt-2 mt-2">
                            <span class="badge ${badgeClass} rounded-pill">${n.status}</span>
                            <span class="text-muted small">
                                <i class="fa-regular fa-clock"></i> ${n.latency}ms
                            </span>
                        </div>
                    </div>
                </div>
            </div>`;
        }).join('');
        
        const badge = document.getElementById('inf-count-badge');
        if(badge) badge.innerText = nodes.length;
    }
}

// --- 渲染服务器列表 ---
function renderServers(serversMap) {
    const list = Object.values(serversMap);
    const tbody = document.getElementById('srv-tbody');
    
    if (tbody) {
        if (list.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted p-5">暂无数据 (Zabbix 连接中...)</td></tr>`;
        } else {
            tbody.innerHTML = list.map(s => {
                const statusBadge = s.status === 'online' 
                    ? '<span class="badge bg-success">在线</span>' 
                    : '<span class="badge bg-danger">离线</span>';
                
                const renderProgress = (val) => {
                    const colorClass = val > 85 ? 'bg-danger' : (val > 60 ? 'bg-warning' : 'bg-primary');
                    return `
                    <div class="d-flex align-items-center" style="gap:10px">
                        <div class="progress flex-grow-1" style="height: 6px; background-color: #e9ecef;">
                            <div class="progress-bar ${colorClass}" role="progressbar" style="width: ${Math.min(val,100)}%"></div>
                        </div>
                        <span class="small text-muted fw-bold" style="width:35px; text-align:right;">${val}%</span>
                    </div>`;
                };

                return `
                <tr>
                    <td class="font-monospace fw-bold text-primary">${s.ip}</td>
                    <td>${statusBadge}</td>
                    <td style="width: 25%">${renderProgress(s.cpu)}</td>
                    <td style="width: 25%">${renderProgress(s.mem)}</td>
                    <td class="font-monospace">${s.disk}%</td>
                    <td class="text-muted small"><i class="fa-regular fa-clock me-1"></i>${s.uptime}</td>
                </tr>`;
            }).join('');
        }
    }
}

// --- 数据库按需检测逻辑 ---
window.checkDB = async function() {
    const btn = document.getElementById('btn-check-db');
    const originalContent = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>检测中...`;
    
    try {
        const res = await fetch('/api/check_db');
        if(!res.ok) throw new Error(`Status ${res.status}`);
        const data = await res.json();
        
        renderDBTopology(data);
        
        btn.innerHTML = `<i class="fa-solid fa-rotate-right me-2"></i> 重新检测`;
        btn.className = "btn btn-outline-primary btn-sm";
    } catch (e) {
        alert("数据库检测失败: " + e.message);
        btn.innerHTML = originalContent;
    } finally {
        btn.disabled = false;
    }
}

function renderDBTopology(data) {
    const masterContainer = document.getElementById('db-master-container');
    const slavesContainer = document.getElementById('db-slaves-container');
    
    // 渲染 Master
    const m = data.master;
    masterContainer.innerHTML = `
        <div class="card border-primary border-2 shadow-sm d-inline-block text-start" style="min-width: 320px; max-width: 100%;">
            <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                <span class="fw-bold"><i class="fa-solid fa-database me-2"></i>主库 (Master)</span>
                <span class="font-monospace bg-white text-primary px-2 rounded small">${m.ip}</span>
            </div>
            <div class="card-body">
                <div class="d-flex justify-content-between mb-2 border-bottom pb-2">
                    <span class="text-muted">连接状态</span>
                    <span class="badge ${m.connected?'bg-success':'bg-danger'}">${m.connected?'已连接':'错误'}</span>
                </div>
                <div class="d-flex justify-content-between mb-2">
                    <span class="text-muted">连接数 (当前/最大)</span>
                    <span class="fw-bold font-monospace">${m.conn_curr} / ${m.conn_max}</span>
                </div>
                <div class="d-flex justify-content-between mb-2">
                    <span class="text-muted">实时 QPS</span>
                    <span class="fw-bold text-success font-monospace">${m.qps || 0}</span>
                </div>
                <div class="bg-light p-2 rounded border mt-2">
                    <div class="small text-muted mb-1">Binlog 位点</div>
                    <div class="font-monospace small text-truncate" title="${m.file}:${m.pos}">
                        ${m.file || 'N/A'}:${m.pos || 0}
                    </div>
                </div>
            </div>
            <div class="card-footer bg-white text-end border-0">
                <button class="btn btn-outline-primary btn-sm w-100" onclick="showDBDetails('${m.ip}')">
                    查看详细指标
                </button>
            </div>
        </div>
    `;
    masterContainer.className = "text-center mb-4"; 

    // 渲染 Slaves
    if (data.slaves.length === 0) {
        slavesContainer.innerHTML = '<div class="col-12 text-center text-muted py-4">无从库配置</div>';
    } else {
        slavesContainer.innerHTML = data.slaves.map(s => {
            const isSync = s.io === 'Yes' && s.sql === 'Yes';
            let delayColor = 'text-success';
            if(s.delay > 60) delayColor = 'text-danger';
            else if(s.delay > 0) delayColor = 'text-warning';
            
            const borderClass = isSync ? 'border-success' : 'border-danger';

            return `
            <div class="col">
                <div class="card h-100 shadow-sm border-top border-4 ${borderClass}">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <span class="fw-bold text-dark"><i class="fa-solid fa-server me-1"></i> 从库 (Slave)</span>
                            <span class="text-muted small font-monospace bg-light px-1 rounded">${s.ip}</span>
                        </div>
                        
                        <div class="row g-2 mb-3 text-center">
                            <div class="col-6">
                                <div class="border rounded p-1">
                                    <div class="small text-muted">IO 线程</div>
                                    <div class="fw-bold ${s.io==='Yes'?'text-success':'text-danger'}">${s.io}</div>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="border rounded p-1">
                                    <div class="small text-muted">SQL 线程</div>
                                    <div class="fw-bold ${s.sql==='Yes'?'text-success':'text-danger'}">${s.sql}</div>
                                </div>
                            </div>
                        </div>

                        <div class="d-flex justify-content-between align-items-center px-2">
                            <span class="text-muted small">延迟</span>
                            <span class="fw-bold font-monospace ${delayColor}">
                                ${s.delay === -1 ? '未知' : s.delay + 's'}
                            </span>
                        </div>
                        
                        ${s.error ? `
                        <div class="alert alert-danger p-2 small mt-3 mb-0 d-flex align-items-start">
                            <i class="fa-solid fa-circle-exclamation mt-1 me-2"></i>
                            <div class="text-break">${s.error.substring(0,50)}...</div>
                        </div>` : ''}
                    </div>
                    <div class="card-footer bg-white text-end border-0">
                         <button class="btn btn-outline-secondary btn-sm w-100" onclick="showDBDetails('${s.ip}')">
                            查看详情
                         </button>
                    </div>
                </div>
            </div>`;
        }).join('');
    }
}

// --- 详情模态框逻辑 ---
window.showDBDetails = async function(ip) {
    if(detailsModal) detailsModal.show();
    
    const content = document.getElementById('modal-json');
    content.innerHTML = `<div class="text-center py-5"><div class="spinner-border text-light" role="status"></div><div class="mt-2">正在查询深度指标...</div></div>`;
    
    try {
        const res = await fetch(`/api/db_details/${ip}`);
        const data = await res.json();
        
        if(data.error) {
            content.innerHTML = `<div class="alert alert-danger m-3">${data.error}</div>`;
            return;
        }

        let html = `<div class="p-2">`;
        
        // InnoDB Section
        if(data.innodb) {
            html += `
            <h6 class="text-info border-bottom border-secondary pb-2 mb-3"><i class="fa-solid fa-memory me-2"></i>InnoDB 缓冲池</h6>
            <div class="row mb-4 g-3">
                <div class="col-md-6">
                    <div class="bg-dark border border-secondary rounded p-3 text-center">
                        <div class="text-muted small mb-1">缓冲池大小</div>
                        <div class="fs-4 fw-bold">${data.innodb.buffer_pool_mb} MB</div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="bg-dark border border-secondary rounded p-3 text-center">
                        <div class="text-muted small mb-1">命中率</div>
                        <div class="fs-4 fw-bold text-success">${data.innodb.hit_rate}</div>
                    </div>
                </div>
            </div>`;
        }

        // Slow Queries Section
        html += `<h6 class="text-warning border-bottom border-secondary pb-2 mb-3"><i class="fa-solid fa-hourglass-half me-2"></i>慢查询 (Top 5)</h6>`;
        if(data.slow_queries && data.slow_queries.length > 0) {
            html += `<div class="list-group mb-4">`;
            data.slow_queries.forEach(q => {
                html += `
                <div class="list-group-item list-group-item-action bg-dark text-white border-secondary">
                    <div class="d-flex w-100 justify-content-between">
                        <h6 class="mb-1 text-danger fw-bold">${parseFloat(q.time).toFixed(4)}s</h6>
                        <small class="text-muted">返回行: ${q.rows_sent}</small>
                    </div>
                    <p class="mb-1 font-monospace small text-break" style="color:#d1d5db;">${q.sql_text ? q.sql_text.substring(0, 200) : 'N/A'}</p>
                </div>`;
            });
            html += `</div>`;
        } else {
            html += `<div class="text-muted fst-italic mb-4">暂无慢查询记录</div>`;
        }
        
        // Tables Section
        if(data.tables && data.tables.length > 0) {
             html += `<h6 class="text-info border-bottom border-secondary pb-2 mb-3"><i class="fa-solid fa-table me-2"></i>最大表 (Top 5)</h6>
             <table class="table table-dark table-sm table-striped small">
                <thead><tr><th>数据库</th><th>表名</th><th class="text-end">大小 (MB)</th></tr></thead>
                <tbody>
             `;
             data.tables.forEach(t => {
                 html += `<tr><td>${t.db}</td><td>${t.tb}</td><td class="text-end fw-bold">${parseFloat(t.size_mb).toFixed(2)}</td></tr>`;
             });
             html += `</tbody></table>`;
        }

        html += `</div>`;
        content.innerHTML = html;
        
    } catch (e) {
        content.innerHTML = `<div class="alert alert-danger m-3">加载失败: ${e.message}</div>`;
    }
}

window.closeModal = function() {
    if(detailsModal) detailsModal.hide();
}