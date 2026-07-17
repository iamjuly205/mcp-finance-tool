// Global Variables
let currentRange = 'this_month';

// Formatter Helpers
function formatCurrency(amount) {
    return Math.round(amount).toLocaleString('vi-VN').replace(/,/g, '.');
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
        // datetime format in db: YYYY-MM-DD HH:MM:SS
        // Split to format as: HH:MM - DD/MM
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
    
    // Auto remove after 4s
    setTimeout(() => {
        toast.style.animation = 'toast-in 0.3s reverse forwards';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Write logs to simulated console
function appendConsoleLog(direction, data) {
    const consoleLogs = document.getElementById('console-logs');
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
        const res = await fetch(`/api/transactions?time_range=${range}`);
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

// Main render orchestrator
async function reloadDashboard() {
    const summary = await fetchSummary();
    const transactions = await fetchTransactions(currentRange);
    const budgets = await fetchBudgets();
    
    // Update stats values
    document.getElementById('total-income').textContent = `${formatCurrency(summary.tong_thu)}đ`;
    document.getElementById('total-expense').textContent = `${formatCurrency(summary.tong_chi)}đ`;
    
    const balance = summary.tong_thu - summary.tong_chi;
    const balanceEl = document.getElementById('net-balance');
    balanceEl.textContent = `${formatCurrency(balance)}đ`;
    if (balance < 0) {
        balanceEl.className = 'stat-value text-red';
    } else {
        balanceEl.className = 'stat-value text-green';
    }
    
    // Update Wallet Card
    document.getElementById('card-balance').textContent = `${formatCurrency(balance)}đ`;
    
    // Render recent transactions
    renderTransactionsTable(transactions);
    
    // Render budgets progress bars
    renderBudgetsSection(budgets);
    
    // Draw categories chart
    renderChart(transactions);
}

// Render Transactions Table
function renderTransactionsTable(transactions) {
    const tbody = document.getElementById('transaction-rows');
    tbody.innerHTML = '';
    
    if (transactions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">Không có giao dịch nào trong khoảng thời gian này.</td></tr>';
        return;
    }
    
    transactions.forEach(t => {
        const tr = document.createElement('tr');
        tr.id = `tx-row-${t.id}`;
        
        const badgeClass = t.type === 'thu' ? 'badge-thu' : 'badge-chi';
        const typeLabel = t.type === 'thu' ? 'Thu nhập' : 'Chi tiêu';
        const amountSign = t.type === 'thu' ? '+' : '-';
        const amountColor = t.type === 'thu' ? 'text-green' : 'text-red';
        
        tr.innerHTML = `
            <td>${formatDate(t.created_at)}</td>
            <td><span class="budget-category">${t.category}</span></td>
            <td><span class="tr-type-badge ${badgeClass}">${typeLabel}</span></td>
            <td><span class="text-secondary">${t.description || '-'}</span></td>
            <td class="text-right ${amountColor} font-semibold">${amountSign}${formatCurrency(t.amount)}đ</td>
        `;
        tbody.appendChild(tr);
    });
}

// Render Budgets Progress
function renderBudgetsSection(budgets) {
    const container = document.getElementById('budget-container');
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
            warningText = `<span class="budget-warning-text text-amber"><i class="fa-solid fa-circle-exclamation"></i> Chi tiêu đã đạt ${b.percentage}% hạn mức!</span>`;
        }
        
        div.innerHTML = `
            <div class="budget-info">
                <span class="budget-category">${b.category}</span>
                <span class="budget-vals">${formatCurrency(b.spent)}đ / ${formatCurrency(b.limit)}đ</span>
            </div>
            <div class="budget-bar-bg">
                <div class="budget-bar-fill ${colorClass}" style="width: ${b.percentage}%"></div>
            </div>
            ${warningText}
        `;
        container.appendChild(div);
    });
}

// Render Donut Chart
let expenseChartInstance = null;

function renderChart(transactions) {
    const canvas = document.getElementById('expense-donut-chart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    // Filter out only spending ('chi')
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
    
    const colors = [
        '#EF4444', // Red
        '#3B82F6', // Blue
        '#F59E0B', // Amber
        '#8B5CF6', // Purple
        '#EC4899', // Pink
        '#14B8A6', // Teal
        '#10B981', // Emerald
    ];
    
    expenseChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors.slice(0, labels.length),
                borderColor: 'rgba(7, 9, 19, 0.8)',
                borderWidth: 2,
                hoverOffset: 4
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
                        label: function(context) {
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

// Document Ready Setup
document.addEventListener('DOMContentLoaded', () => {
    // 1. Initial Reload
    reloadDashboard();
    
    // 2. Setup Filter Buttons
    const filterBtns = document.querySelectorAll('.filter-btn');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentRange = btn.dataset.range;
            reloadDashboard();
            showToast(`Đã lọc giao dịch theo: ${btn.textContent}`, 'info');
        });
    });
    
    // 3. Setup Modals Behavior
    const txModal = document.getElementById('tx-modal');
    const budgetModal = document.getElementById('budget-modal');
    
    document.getElementById('open-tx-modal').addEventListener('click', () => txModal.classList.add('show'));
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

    // 4. Setup Forms submits
    // Transaction Submit
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
            reloadDashboard();
        } catch (err) {
            showToast('Không thể lưu giao dịch. Lỗi máy chủ.', 'error');
        }
    });

    // Budget Submit
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
            reloadDashboard();
        } catch (err) {
            showToast('Không thể thiết lập ngân sách.', 'error');
        }
    });

    // 5. Setup Undo Action
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

    // 6. MCP Simulated Robot Chat & Console
    const chatContainer = document.getElementById('chat-messages-container');
    const consoleLogs = document.getElementById('console-logs');
    
    document.getElementById('btn-clear-console').addEventListener('click', () => {
        consoleLogs.innerHTML = '<div class="console-line info">[System] Console logs cleared. Ready...</div>';
    });

    document.getElementById('chat-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const inputEl = document.getElementById('chat-input');
        const text = inputEl.value.trim();
        if (!text) return;
        
        // Add user bubble
        const userBubble = document.createElement('div');
        userBubble.className = 'chat-bubble user-bubble';
        userBubble.textContent = text;
        chatContainer.appendChild(userBubble);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        inputEl.value = '';
        
        // Add pending bot bubble
        const pendingBubble = document.createElement('div');
        pendingBubble.className = 'chat-bubble bot-bubble';
        pendingBubble.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Robot đang xử lý...';
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
            
            // Write to JSON RPC console
            if (data.rpc_call) {
                appendConsoleLog('req', data.rpc_call);
                setTimeout(() => {
                    appendConsoleLog('res', data.rpc_response);
                }, 400);
                
                // Show toast for warning if any
                if (data.tts.includes('Cảnh báo')) {
                    showToast(data.tts.split('.')[1] || 'Cảnh báo ngân sách!', 'warning');
                } else {
                    showToast('Đã ghi nhận giao dịch từ robot!', 'success');
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

    // 7. Wallet 3D Tilt Hover effect
    const walletCard = document.getElementById('digital-wallet-card');
    if (walletCard) {
        walletCard.addEventListener('mousemove', (e) => {
            const rect = walletCard.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const xPercent = (x / rect.width) * 100;
            const yPercent = (y / rect.height) * 100;
            
            const rotateY = ((xPercent - 50) / 50) * 15;
            const rotateX = -(((yPercent - 50) / 50) * 15);
            
            walletCard.style.transform = `rotateY(${rotateY}deg) rotateX(${rotateX}deg) translateY(-5px)`;
            
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
});
