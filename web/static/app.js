// Global Dashboard State
let currentRange = 'this_month';
let currentTypeFilter = 'all';
let currentCategoryFilter = 'all';
let searchQuery = '';
let isPrivacyHidden = false;
let activeChartTab = 'donut';

let rawTransactionsList = [];
let rawKeywordsList = [];
let expenseChartInstance = null;
let cashflowChartInstance = null;

// Formatter Helpers
function formatCurrency(amount) {
    if (isNaN(amount)) return '0';
    return Math.round(amount).toLocaleString('vi-VN').replace(/,/g, '.');
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
        const parts = dateStr.split(' ');
        if (parts.length < 2) return dateStr;
        const dateParts = parts[0].split('-');
        const timeParts = parts[1].split(':');
        return `${timeParts[0]}:${timeParts[1]} - ${dateParts[2]}/${dateParts[1]}`;
    } catch (e) {
        return dateStr;
    }
}

// Notification Toast System
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    let icon = 'fa-info-circle';
    if (type === 'success') icon = 'fa-check-circle';
    else if (type === 'warning') icon = 'fa-exclamation-triangle';
    else if (type === 'error') icon = 'fa-times-circle';

    toast.innerHTML = `
        <i class="fa-solid ${icon}"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    // Auto remove after 3.5s
    setTimeout(() => {
        toast.style.animation = 'toast-in 0.3s reverse forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// Write logs to simulated console
function appendConsoleLog(direction, data) {
    const consoleLogs = document.getElementById('console-logs');
    if (!consoleLogs) return;
    const line = document.createElement('div');

    if (direction === 'req') {
        line.className = 'console-line req';
        line.textContent = `--> SEND CLIENT: ${JSON.stringify(data, null, 2)}`;
    } else if (direction === 'res') {
        line.className = 'console-line res';
        line.textContent = `<-- RECV SERVER: ${JSON.stringify(data, null, 2)}`;
    } else if (direction === 'error') {
        line.className = 'console-line err';
        line.textContent = `[Error] ${data}`;
    } else {
        line.className = 'console-line info';
        line.textContent = `[Info] ${data}`;
    }

    consoleLogs.appendChild(line);
    consoleLogs.scrollTop = consoleLogs.scrollHeight;
}

// API Call Wrappers
async function fetchSummary() {
    try {
        const res = await fetch('/api/summary');
        if (!res.ok) throw new Error('API Error');
        return await res.json();
    } catch (e) {
        showToast('Không thể tải tóm tắt tài chính.', 'error');
        return { tong_thu: 0, tong_chi: 0 };
    }
}

async function fetchTransactions(range) {
    try {
        const res = await fetch(`/api/transactions?time_range=${range}&limit=200`);
        if (!res.ok) throw new Error('API Error');
        return await res.json();
    } catch (e) {
        showToast('Không thể tải lịch sử giao dịch.', 'error');
        return [];
    }
}

async function fetchBudgets() {
    try {
        const res = await fetch('/api/budgets');
        if (!res.ok) throw new Error('API Error');
        return await res.json();
    } catch (e) {
        showToast('Không thể tải ngân sách hạn mức.', 'error');
        return [];
    }
}

// Main Dashboard Reload Orchestrator
async function reloadDashboard() {
    const summary = await fetchSummary();
    rawTransactionsList = await fetchTransactions(currentRange);
    const budgets = await fetchBudgets();

    // Tải danh sách từ khóa
    reloadKeywordsList();

    // Update summary stats
    updateSummaryStats(summary, rawTransactionsList);

    // Render recent transactions with current active filters
    renderTransactionsTable();

    // Render budgets progress bars
    renderBudgetsSection(budgets);

    // Draw categories & cashflow charts
    renderCharts(rawTransactionsList);
}

// Update 4 Summary Stat Cards
function updateSummaryStats(summary, transactions) {
    const totalIncomeEl = document.getElementById('total-income');
    const totalExpenseEl = document.getElementById('total-expense');
    const netBalanceEl = document.getElementById('net-balance');
    const cardBalanceEl = document.getElementById('card-balance');
    const totalTxCountEl = document.getElementById('total-tx-count');
    const avgTxDescEl = document.getElementById('avg-tx-desc');

    if (totalIncomeEl) totalIncomeEl.textContent = `${formatCurrency(summary.tong_thu)}đ`;
    if (totalExpenseEl) totalExpenseEl.textContent = `${formatCurrency(summary.tong_chi)}đ`;

    const balance = summary.tong_thu - summary.tong_chi;
    if (netBalanceEl) {
        netBalanceEl.textContent = `${formatCurrency(balance)}đ`;
        netBalanceEl.className = balance < 0 ? 'stat-value text-red text-privacy' : 'stat-value text-green text-privacy';
    }

    if (cardBalanceEl) {
        cardBalanceEl.textContent = `${formatCurrency(balance)}đ`;
    }

    if (totalTxCountEl) {
        totalTxCountEl.textContent = transactions.length;
    }

    if (avgTxDescEl) {
        if (transactions.length > 0) {
            const totalSpent = transactions.filter(t => t.type === 'chi').reduce((sum, t) => sum + t.amount, 0);
            avgTxDescEl.innerHTML = `<i class="fa-solid fa-calculator"></i> Chi TB: ${formatCurrency(totalSpent / (transactions.length || 1))}đ/lần`;
        } else {
            avgTxDescEl.innerHTML = `<i class="fa-solid fa-info-circle"></i> Chưa có giao dịch`;
        }
    }

    // Privacy Masking Toggle state apply
    applyPrivacyState();
}

// Privacy State Helper
function applyPrivacyState() {
    const privacyElements = document.querySelectorAll('.text-privacy');
    const privacyIcon = document.getElementById('privacy-icon');

    privacyElements.forEach(el => {
        if (isPrivacyHidden) {
            el.classList.add('is-hidden-privacy');
        } else {
            el.classList.remove('is-hidden-privacy');
        }
    });

    if (privacyIcon) {
        if (isPrivacyHidden) {
            privacyIcon.className = 'fa-solid fa-eye-slash';
        } else {
            privacyIcon.className = 'fa-solid fa-eye';
        }
    }
}

// Filter and Render Transactions Table
function renderTransactionsTable() {
    const tbody = document.getElementById('transaction-rows');
    if (!tbody) return;
    tbody.innerHTML = '';

    // Apply Client Filters (Search query, Type, Category)
    const filtered = rawTransactionsList.filter(t => {
        // 1. Type Filter
        if (currentTypeFilter !== 'all' && t.type !== currentTypeFilter) return false;

        // 2. Category Filter
        if (currentCategoryFilter !== 'all' && t.category !== currentCategoryFilter) return false;

        // 3. Search Query (matches description or category or amount)
        if (searchQuery) {
            const q = searchQuery.toLowerCase();
            const descMatch = (t.description || '').toLowerCase().includes(q);
            const catMatch = (t.category || '').toLowerCase().includes(q);
            const amountMatch = t.amount.toString().includes(q);
            if (!descMatch && !catMatch && !amountMatch) return false;
        }

        return true;
    });

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-state">Không tìm thấy giao dịch phù hợp với bộ lọc.</td></tr>';
        return;
    }

    filtered.forEach(t => {
        const tr = document.createElement('tr');
        tr.id = `tx-row-${t.id}`;

        const badgeClass = t.type === 'thu' ? 'badge-thu' : 'badge-chi';
        const typeLabel = t.type === 'thu' ? 'Thu nhập' : 'Chi tiêu';
        const amountSign = t.type === 'thu' ? '+' : '-';
        const amountColor = t.type === 'thu' ? 'text-green' : 'text-red';

        tr.innerHTML = `
            <td><span class="text-muted">${formatDate(t.created_at)}</span></td>
            <td><span class="budget-category">${t.category}</span></td>
            <td><span class="tr-type-badge ${badgeClass}">${typeLabel}</span></td>
            <td><span>${t.description || '-'}</span></td>
            <td class="text-right ${amountColor} font-semibold text-privacy">${amountSign}${formatCurrency(t.amount)}đ</td>
            <td class="text-center">
                <button class="btn-delete-tx" data-id="${t.id}" title="Xóa giao dịch này">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    // Attach single transaction delete listeners
    tbody.querySelectorAll('.btn-delete-tx').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const txId = btn.dataset.id;
            if (confirm(`Bạn có chắc muốn xóa giao dịch ID #${txId}?`)) {
                try {
                    const res = await fetch(`/api/transactions/${txId}`, { method: 'DELETE' });
                    if (!res.ok) throw new Error('API Error');
                    const data = await res.json();
                    showToast(data.message, 'success');
                    reloadDashboard();
                } catch (err) {
                    showToast('Không thể xóa giao dịch.', 'error');
                }
            }
        });
    });

    applyPrivacyState();
}

// Render Budgets Progress Section
function renderBudgetsSection(budgets) {
    const container = document.getElementById('budget-container');
    if (!container) return;
    container.innerHTML = '';

    if (budgets.length === 0) {
        container.innerHTML = '<div class="empty-state">Chưa thiết lập hạn mức nào.</div>';
        return;
    }

    budgets.forEach(b => {
        const div = document.createElement('div');
        div.className = 'budget-item';

        let colorClass = 'bg-green';
        let warningText = '';

        if (b.spent > b.limit) {
            colorClass = 'bg-red';
            warningText = `<span class="budget-warning-text text-red"><i class="fa-solid fa-triangle-exclamation"></i> Vượt hạn mức ${formatCurrency(b.over)}đ!</span>`;
        } else if (b.spent >= b.limit * 0.8) {
            colorClass = 'bg-amber';
            warningText = `<span class="budget-warning-text text-amber"><i class="fa-solid fa-circle-exclamation"></i> Chi tiêu đã đạt ${b.percentage}%</span>`;
        } else {
            warningText = `<span class="budget-warning-text text-green"><i class="fa-solid fa-check-circle"></i> Đang trong tầm kiểm soát</span>`;
        }

        div.innerHTML = `
            <div class="budget-info">
                <span class="budget-category-title"><i class="fa-solid fa-folder-open text-blue"></i> ${b.category}</span>
                <span class="budget-vals text-privacy">${formatCurrency(b.spent)}đ / ${formatCurrency(b.limit)}đ</span>
            </div>
            <div class="budget-bar-bg">
                <div class="budget-bar-fill ${colorClass}" style="width: ${b.percentage}%"></div>
            </div>
            <div class="budget-bottom-row">
                ${warningText}
                <button class="btn-delete-budget" data-category="${b.category}" title="Xóa hạn mức">
                    <i class="fa-solid fa-trash-can"></i> Xóa
                </button>
            </div>
        `;
        container.appendChild(div);
    });

    // Delete Budget Event Handlers
    container.querySelectorAll('.btn-delete-budget').forEach(btn => {
        btn.addEventListener('click', async () => {
            const cat = btn.dataset.category;
            if (confirm(`Bạn có chắc muốn xóa hạn mức chi tiêu cho hạng mục "${cat}"?`)) {
                try {
                    const res = await fetch(`/api/budgets/${encodeURIComponent(cat)}`, { method: 'DELETE' });
                    if (!res.ok) throw new Error('API Error');
                    const data = await res.json();
                    showToast(data.message, 'success');
                    reloadDashboard();
                } catch (err) {
                    showToast('Không thể xóa hạn mức ngân sách.', 'error');
                }
            }
        });
    });

    applyPrivacyState();
}

// Render Dual Charts (Donut + Bar Chart)
function renderCharts(transactions) {
    renderDonutChart(transactions);
    renderBarChart(transactions);
}

function renderDonutChart(transactions) {
    const canvas = document.getElementById('expense-donut-chart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    // Filter spent transactions ('chi')
    const spentTxs = transactions.filter(t => t.type === 'chi');

    // Group by category
    const categoryTotals = {};
    spentTxs.forEach(t => {
        categoryTotals[t.category] = (categoryTotals[t.category] || 0) + t.amount;
    });

    const labels = Object.keys(categoryTotals);
    const data = Object.values(categoryTotals);

    if (expenseChartInstance) {
        expenseChartInstance.destroy();
    }

    if (labels.length === 0) {
        expenseChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Chưa có dữ liệu chi tiêu'],
                datasets: [{
                    data: [1],
                    backgroundColor: ['rgba(255, 255, 255, 0.05)'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#9CA3AF', font: { family: 'Outfit' } }
                    }
                }
            }
        });
        return;
    }

    const colors = ['#10B981', '#34D399', '#059669', '#047857', '#065f46', '#6EE7B7', '#A7F3D0'];

    expenseChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors.slice(0, labels.length),
                borderColor: 'rgba(5, 8, 7, 0.9)',
                borderWidth: 2,
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#F3F4F6',
                        font: { family: 'Outfit', size: 12 },
                        padding: 15
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const val = context.raw;
                            return ` ${context.label}: ${formatCurrency(val)}đ`;
                        }
                    }
                }
            },
            cutout: '65%'
        }
    });
}

function renderBarChart(transactions) {
    const canvas = document.getElementById('cashflow-bar-chart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const totalIncome = transactions.filter(t => t.type === 'thu').reduce((sum, t) => sum + t.amount, 0);
    const totalExpense = transactions.filter(t => t.type === 'chi').reduce((sum, t) => sum + t.amount, 0);

    if (cashflowChartInstance) {
        cashflowChartInstance.destroy();
    }

    cashflowChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Thu nhập', 'Chi tiêu'],
            datasets: [{
                label: 'Số tiền (VNĐ)',
                data: [totalIncome, totalExpense],
                backgroundColor: ['rgba(16, 185, 129, 0.85)', 'rgba(239, 68, 68, 0.85)'],
                borderColor: ['#10B981', '#EF4444'],
                borderWidth: 1,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            return ` ${context.label}: ${formatCurrency(context.raw)}đ`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#9CA3AF', font: { family: 'Outfit' } },
                    grid: { display: false }
                },
                y: {
                    ticks: {
                        color: '#9CA3AF',
                        font: { family: 'Outfit' },
                        callback: function (val) { return formatCurrency(val) + 'đ'; }
                    },
                    grid: { color: 'rgba(255, 255, 255, 0.05)' }
                }
            }
        }
    });
}

async function checkMCPStatusRealtime() {
    const indicator = document.querySelector('.status-indicator');
    const statusVal = document.querySelector('.status-value');
    if (!indicator || !statusVal) return;

    try {
        const res = await fetch('/api/mcp-status');
        if (!res.ok) throw new Error('API Error');
        const data = await res.json();

        if (data.status === 'connected') {
            indicator.className = 'status-indicator online';
            statusVal.textContent = 'Connected (Bridge Active)';
            statusVal.style.color = '#10B981';
        } else if (data.status === 'connecting') {
            indicator.className = 'status-indicator warning';
            statusVal.textContent = 'Connecting...';
            statusVal.style.color = '#F59E0B';
        } else {
            indicator.className = 'status-indicator offline';
            statusVal.textContent = 'Disconnected (Offline)';
            statusVal.style.color = '#EF4444';
        }
    } catch (err) {
        indicator.className = 'status-indicator offline';
        statusVal.textContent = 'Disconnected';
        statusVal.style.color = '#EF4444';
    }
}

    // Document Ready Initialization & Event Binding
    document.addEventListener('DOMContentLoaded', () => {
        // 1. Initial Dashboard Load & Real-time MCP Status Check
        reloadDashboard();
        checkMCPStatusRealtime();
        setInterval(checkMCPStatusRealtime, 3000);

        // 2. Setup Time Range Filter Buttons
        const filterBtns = document.querySelectorAll('.filter-btn');
        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                filterBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentRange = btn.dataset.range;
                reloadDashboard();
                showToast(`Đã lọc giao dịch: ${btn.textContent}`, 'info');
            });
        });

        // 3. Setup Dropdown Filters (Type & Category)
        const typeSelect = document.getElementById('filter-type-select');
        if (typeSelect) {
            typeSelect.addEventListener('change', (e) => {
                currentTypeFilter = e.target.value;
                renderTransactionsTable();
            });
        }

        const catSelect = document.getElementById('filter-category-select');
        if (catSelect) {
            catSelect.addEventListener('change', (e) => {
                currentCategoryFilter = e.target.value;
                renderTransactionsTable();
            });
        }

        // 4. Header & Keyword Search Inputs
        const headerSearch = document.getElementById('header-search-input');
        if (headerSearch) {
            headerSearch.addEventListener('input', (e) => {
                searchQuery = e.target.value.trim();
                renderTransactionsTable();
            });
        }

        const keywordSearch = document.getElementById('keyword-search-input');
        if (keywordSearch) {
            keywordSearch.addEventListener('input', (e) => {
                const q = e.target.value.toLowerCase().trim();
                const filteredKw = rawKeywordsList.filter(kw =>
                    kw.keyword.toLowerCase().includes(q) ||
                    kw.category.toLowerCase().includes(q)
                );
                renderKeywords(filteredKw);
            });
        }

        // 5. Privacy Toggle Button
        const privacyBtn = document.getElementById('btn-toggle-privacy');
        if (privacyBtn) {
            privacyBtn.addEventListener('click', () => {
                isPrivacyHidden = !isPrivacyHidden;
                applyPrivacyState();
                showToast(isPrivacyHidden ? 'Đã ẩn số dư tài khoản' : 'Đã hiện số dư tài khoản', 'info');
            });
        }

        // 6. Chart Switcher Tabs
        const btnDonut = document.getElementById('btn-chart-donut');
        const btnBar = document.getElementById('btn-chart-bar');
        const viewDonut = document.getElementById('chart-view-donut');
        const viewBar = document.getElementById('chart-view-bar');

        if (btnDonut && btnBar) {
            btnDonut.addEventListener('click', () => {
                btnDonut.classList.add('active');
                btnBar.classList.remove('active');
                viewDonut.classList.remove('hidden');
                viewBar.classList.add('hidden');
                activeChartTab = 'donut';
                renderDonutChart(rawTransactionsList);
            });

            btnBar.addEventListener('click', () => {
                btnBar.classList.add('active');
                btnDonut.classList.remove('active');
                viewBar.classList.remove('hidden');
                viewDonut.classList.add('hidden');
                activeChartTab = 'bar';
                renderBarChart(rawTransactionsList);
            });
        }

        // 7. Setup Modals Behavior
        const txModal = document.getElementById('tx-modal');
        const budgetModal = document.getElementById('budget-modal');

        document.getElementById('open-tx-modal').addEventListener('click', () => txModal.classList.add('show'));
        const btnQuickAdd = document.getElementById('btn-quick-add-tx');
        if (btnQuickAdd) btnQuickAdd.addEventListener('click', () => txModal.classList.add('show'));

        document.getElementById('close-tx-modal').addEventListener('click', () => txModal.classList.remove('show'));
        document.getElementById('cancel-tx-modal').addEventListener('click', () => txModal.classList.remove('show'));

        document.getElementById('open-budget-modal').addEventListener('click', () => budgetModal.classList.add('show'));
        document.getElementById('close-budget-modal-btn').addEventListener('click', () => budgetModal.classList.remove('show'));
        document.getElementById('cancel-budget-modal').addEventListener('click', () => budgetModal.classList.remove('show'));

        // Close modals on clicking backdrop
        window.addEventListener('click', (e) => {
            if (e.target === txModal) txModal.classList.remove('show');
            if (e.target === budgetModal) budgetModal.classList.remove('show');
        });

        // Preset Amount Chips & Dynamic Amount Preview
        const txAmountInput = document.getElementById('tx-amount');
        const txAmountPreview = document.getElementById('tx-amount-preview');

        if (txAmountInput && txAmountPreview) {
            txAmountInput.addEventListener('input', () => {
                const val = parseFloat(txAmountInput.value) || 0;
                txAmountPreview.textContent = `${formatCurrency(val)} VNĐ`;
            });

            document.querySelectorAll('.preset-btn[data-add]').forEach(btn => {
                btn.addEventListener('click', () => {
                    const currentVal = parseFloat(txAmountInput.value) || 0;
                    const addVal = parseFloat(btn.dataset.add);
                    const newVal = currentVal + addVal;
                    txAmountInput.value = newVal;
                    txAmountPreview.textContent = `${formatCurrency(newVal)} VNĐ`;
                });
            });
        }

        const budgetAmountInput = document.getElementById('budget-amount');
        const budgetAmountPreview = document.getElementById('budget-amount-preview');

        if (budgetAmountInput && budgetAmountPreview) {
            budgetAmountInput.addEventListener('input', () => {
                const val = parseFloat(budgetAmountInput.value) || 0;
                budgetAmountPreview.textContent = `${formatCurrency(val)} VNĐ`;
            });

            document.querySelectorAll('.preset-btn[data-add-budget]').forEach(btn => {
                btn.addEventListener('click', () => {
                    const addVal = parseFloat(btn.dataset.addBudget);
                    budgetAmountInput.value = addVal;
                    budgetAmountPreview.textContent = `${formatCurrency(addVal)} VNĐ`;
                });
            });
        }

        // 8. Forms Submit Handlers
        // Transaction Form Submit
        document.getElementById('tx-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const type = document.querySelector('input[name="transaction_type"]:checked').value;
            const amount = parseFloat(document.getElementById('tx-amount').value);
            const category = document.getElementById('tx-category').value;
            const description = document.getElementById('tx-desc').value;

            try {
                const res = await fetch('/api/transactions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ transaction_type: type, amount, category, description })
                });

                if (!res.ok) throw new Error('Api Error');
                const data = await res.json();

                showToast(data.message, 'success');
                if (data.warning) {
                    setTimeout(() => showToast(data.warning, 'warning'), 1000);
                }

                txModal.classList.remove('show');
                document.getElementById('tx-form').reset();
                if (txAmountPreview) txAmountPreview.textContent = '0 VNĐ';
                reloadDashboard();
            } catch (err) {
                showToast('Không thể lưu giao dịch. Lỗi máy chủ.', 'error');
            }
        });

        // Budget Form Submit
        document.getElementById('budget-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const category = document.getElementById('budget-category').value;
            const amount = parseFloat(document.getElementById('budget-amount').value);

            try {
                const res = await fetch('/api/budgets', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ category, amount })
                });

                if (!res.ok) throw new Error('Api Error');
                const data = await res.json();

                showToast(data.message, 'success');
                budgetModal.classList.remove('show');
                document.getElementById('budget-form').reset();
                if (budgetAmountPreview) budgetAmountPreview.textContent = '0 VNĐ';
                reloadDashboard();
            } catch (err) {
                showToast('Không thể thiết lập ngân sách.', 'error');
            }
        });

        // 9. Setup Global Undo Action
        document.getElementById('btn-undo').addEventListener('click', async () => {
            try {
                const res = await fetch('/api/transactions/last', { method: 'DELETE' });
                if (!res.ok) throw new Error('Api error');
                const data = await res.json();

                if (data.success) {
                    showToast('Đã hoàn tác giao dịch gần nhất thành công.', 'success');
                    reloadDashboard();
                } else {
                    showToast('Không tìm thấy giao dịch nào để hoàn tác.', 'warning');
                }
            } catch (err) {
                showToast('Lỗi khi thực hiện hoàn tác.', 'error');
            }
        });

        const btnClearHistory = document.getElementById('btn-clear-history');
        if (btnClearHistory) {
            btnClearHistory.addEventListener('click', async () => {
                if (confirm('BẠN CÓ CHẮC CHẮN MUỐN XÓA TOÀN BỘ LỊCH SỬ GIAO DỊCH? Hành động này sẽ đưa tất cả tổng thu, tổng chi và số dư về 0đ và không thể hoàn tác.')) {
                    try {
                        const res = await fetch('/api/transactions', { method: 'DELETE' });
                        if (!res.ok) throw new Error('Api error');
                        const data = await res.json();
                        showToast(data.message, 'success');
                        reloadDashboard();
                    } catch (err) {
                        showToast('Lỗi khi thực hiện xóa toàn bộ lịch sử.', 'error');
                    }
                }
            });
        }

        // 10. AI Chat Sandbox & Prompt Pills
        const chatContainer = document.getElementById('chat-messages-container');
        const consoleLogs = document.getElementById('console-logs');
        const chatForm = document.getElementById('chat-form');
        const chatInput = document.getElementById('chat-input');

        if (document.getElementById('btn-clear-console')) {
            document.getElementById('btn-clear-console').addEventListener('click', () => {
                consoleLogs.innerHTML = '<div class="console-line info">[System] Console logs cleared. Ready...</div>';
            });
        }

        // Handle Quick Prompt Pills click
        document.querySelectorAll('.prompt-pill').forEach(pill => {
            pill.addEventListener('click', () => {
                const promptText = pill.dataset.prompt;
                if (chatInput) {
                    chatInput.value = promptText;
                    chatForm.dispatchEvent(new Event('submit'));
                }
            });
        });

        if (chatForm) {
            chatForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const text = chatInput.value.trim();
                if (!text) return;

                // Add user bubble
                const userBubble = document.createElement('div');
                userBubble.className = 'chat-bubble user-bubble';
                userBubble.textContent = text;
                chatContainer.appendChild(userBubble);
                chatContainer.scrollTop = chatContainer.scrollHeight;

                chatInput.value = '';

                // Add pending bot bubble
                const pendingBubble = document.createElement('div');
                pendingBubble.className = 'chat-bubble bot-bubble';
                pendingBubble.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Robot Xiaozhi đang xử lý...';
                chatContainer.appendChild(pendingBubble);
                chatContainer.scrollTop = chatContainer.scrollHeight;

                try {
                    appendConsoleLog('info', `Gửi tin nhắn phân tích: "${text}"`);

                    const res = await fetch('/api/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: text })
                    });

                    if (!res.ok) throw new Error('Server error');
                    const data = await res.json();

                    // Remove spinner and replace with result
                    pendingBubble.textContent = data.tts;

                    // Log routing source
                    if (data.source === 'keyword') {
                        appendConsoleLog('info', '⚡ Định tuyến bởi: KEYWORD MATCH (Bộ từ khóa SQLite cục bộ)');
                    } else if (data.source === 'llm') {
                        appendConsoleLog('info', '🤖 Định tuyến bởi: GEMINI LLM (Trí tuệ nhân tạo)');
                    } else if (data.source === 'regex') {
                        appendConsoleLog('info', '🔍 Định tuyến bởi: REGEX FALLBACK (Quy tắc mẫu)');
                    }

                    // Write to JSON RPC console
                    if (data.rpc_call) {
                        appendConsoleLog('req', data.rpc_call);
                        setTimeout(() => {
                            appendConsoleLog('res', data.rpc_response);
                        }, 350);

                        if (data.tts.includes('Cảnh báo')) {
                            showToast(data.tts, 'warning');
                        } else {
                            showToast('Đã ghi nhận giao dịch thành công!', 'success');
                        }
                    } else {
                        appendConsoleLog('info', 'Không có Tool Call nào được gọi từ câu lệnh này.');
                    }

                    reloadDashboard();
                } catch (err) {
                    pendingBubble.textContent = 'Xin lỗi, tôi đã gặp lỗi khi xử lý thông tin này.';
                    appendConsoleLog('error', err.message);
                }

                chatContainer.scrollTop = chatContainer.scrollHeight;
            });
        }

        // 11. Web Speech API (Voice Input)
        const micBtn = document.getElementById('btn-mic-record');
        if (micBtn && chatInput) {
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                const recognition = new SpeechRecognition();

                recognition.lang = 'vi-VN';
                recognition.interimResults = false;
                recognition.maxAlternatives = 1;

                let isListening = false;

                micBtn.addEventListener('click', () => {
                    if (!isListening) {
                        recognition.start();
                    } else {
                        recognition.stop();
                    }
                });

                recognition.onstart = () => {
                    isListening = true;
                    micBtn.classList.add('listening');
                    showToast('Đang lắng nghe giọng nói...', 'info');
                };

                recognition.onerror = (event) => {
                    showToast('Lỗi nhận diện giọng nói: ' + event.error, 'error');
                    isListening = false;
                    micBtn.classList.remove('listening');
                };

                recognition.onend = () => {
                    isListening = false;
                    micBtn.classList.remove('listening');
                };

                recognition.onresult = (event) => {
                    const textResult = event.results[0][0].transcript;
                    chatInput.value = textResult;
                    showToast('Đã nhận diện giọng nói!', 'success');
                };
            } else {
                micBtn.style.display = 'none';
            }
        }

        // 12. Digital Card 3D Shimmer Effect
        const walletCard = document.getElementById('digital-wallet-card');
        if (walletCard) {
            walletCard.addEventListener('mousemove', (e) => {
                const rect = walletCard.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                const xPercent = (x / rect.width) * 100;
                const yPercent = (y / rect.height) * 100;

                const rotateY = ((xPercent - 50) / 50) * 12;
                const rotateX = -(((yPercent - 50) / 50) * 12);

                walletCard.style.transform = `rotateY(${rotateY}deg) rotateX(${rotateX}deg) translateY(-4px)`;

                const glow = walletCard.querySelector('.card-glass-glow');
                if (glow) {
                    glow.style.background = `radial-gradient(circle at ${xPercent}% ${yPercent}%, rgba(255, 255, 255, 0.12) 0%, transparent 60%)`;
                }
            });

            walletCard.addEventListener('mouseleave', () => {
                walletCard.style.transform = 'rotateY(0deg) rotateX(0deg) translateY(0)';
                const glow = walletCard.querySelector('.card-glass-glow');
                if (glow) {
                    glow.style.background = 'radial-gradient(circle, rgba(255, 255, 255, 0.08) 0%, transparent 60%)';
                }
            });
        }

        // 13. Mobile Topbar & Sidebar Overlay Toggle
        const mobileMenuBtn = document.getElementById('mobile-menu-toggle');
        const sidebar = document.getElementById('sidebar');
        const sidebarOverlay = document.getElementById('sidebar-overlay');

        if (mobileMenuBtn && sidebar && sidebarOverlay) {
            mobileMenuBtn.addEventListener('click', () => {
                sidebar.classList.toggle('active');
                sidebarOverlay.classList.toggle('active');
            });

            sidebarOverlay.addEventListener('click', () => {
                sidebar.classList.remove('active');
                sidebarOverlay.classList.remove('active');
            });

            document.querySelectorAll('.nav-item').forEach(item => {
                item.addEventListener('click', (e) => {
                    e.preventDefault();
                    sidebar.classList.remove('active');
                    sidebarOverlay.classList.remove('active');

                    // Toggle active class on sidebar items
                    document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
                    item.classList.add('active');

                    // Get target tab id
                    const tabId = item.id.replace('nav-', 'tab-');

                    // Hide all tabs
                    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));

                    // Show target tab
                    const targetTab = document.getElementById(tabId);
                    if (targetTab) {
                        targetTab.classList.add('active');
                    }
                });
            });
        }

        // 14. Keyword Manager Modal and Submit
        const kwModal = document.getElementById('keyword-modal');
        if (kwModal) {
            document.getElementById('open-keyword-modal').addEventListener('click', () => kwModal.classList.add('show'));
            document.getElementById('close-keyword-modal').addEventListener('click', () => kwModal.classList.remove('show'));
            document.getElementById('cancel-keyword-modal').addEventListener('click', () => kwModal.classList.remove('show'));

            window.addEventListener('click', (e) => {
                if (e.target === kwModal) kwModal.classList.remove('show');
            });

            document.getElementById('keyword-form').addEventListener('submit', async (e) => {
                e.preventDefault();
                const keyword = document.getElementById('kw-text').value.trim();
                const category = document.getElementById('kw-category').value;
                const type = document.querySelector('input[name="kw_type"]:checked').value;

                try {
                    const res = await fetch('/api/keywords', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ keyword, category, type })
                    });

                    if (!res.ok) throw new Error('Api Error');
                    const data = await res.json();

                    showToast(data.message, 'success');
                    kwModal.classList.remove('show');
                    document.getElementById('keyword-form').reset();
                    reloadKeywordsList();
                } catch (err) {
                    showToast('Không thể thêm từ khóa.', 'error');
                }
            });
        }
    });

    // Keyword Manager AJAX functions
    async function fetchKeywords() {
        try {
            const res = await fetch('/api/keywords');
            if (!res.ok) throw new Error('API error');
            return await res.json();
        } catch (e) {
            console.error(e);
            return [];
        }
    }

    function renderKeywords(keywords) {
        const tbody = document.getElementById('keyword-rows');
        if (!tbody) return;
        tbody.innerHTML = '';

        if (keywords.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="empty-state">Không tìm thấy từ khóa nào trong hệ thống.</td></tr>';
            return;
        }

        keywords.forEach(kw => {
            const tr = document.createElement('tr');
            tr.id = `kw-row-${kw.id}`;

            const badgeClass = kw.type === 'thu' ? 'badge-thu' : 'badge-chi';
            const typeLabel = kw.type === 'thu' ? 'Thu nhập' : 'Chi tiêu';

            tr.innerHTML = `
            <td><strong class="text-blue">${kw.keyword}</strong></td>
            <td><span class="budget-category">${kw.category}</span></td>
            <td><span class="tr-type-badge ${badgeClass}">${typeLabel}</span></td>
            <td class="text-center">
                <button class="btn-delete-kw" data-id="${kw.id}" title="Xóa từ khóa này">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
            </td>
        `;
            tbody.appendChild(tr);
        });

        // Attach delete listeners
        tbody.querySelectorAll('.btn-delete-kw').forEach(btn => {
            btn.addEventListener('click', async () => {
                const id = btn.dataset.id;
                if (confirm('Bạn chắc chắn muốn xóa từ khóa này?')) {
                    try {
                        const res = await fetch(`/api/keywords/${id}`, { method: 'DELETE' });
                        if (!res.ok) throw new Error('API error');
                        const data = await res.json();
                        showToast(data.message, 'success');
                        reloadKeywordsList();
                    } catch (err) {
                        showToast('Không thể xóa từ khóa.', 'error');
                    }
                }
            });
        });
    }

    async function reloadKeywordsList() {
        rawKeywordsList = await fetchKeywords();
        renderKeywords(rawKeywordsList);
    }
