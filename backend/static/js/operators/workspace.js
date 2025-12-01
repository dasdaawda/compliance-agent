// Operator workspace JavaScript utilities

class OperatorWorkspace {
    constructor() {
        this.currentTriggerId = null;
        this.heartbeatInterval = null;
        this.desyncThreshold = 0.75; // 750ms
        
        this.init();
    }
    
    init() {
        this.startHeartbeat();
        this.setupVideoPlayer();
    }
    
    startHeartbeat() {
        // Send heartbeat every 30 seconds
        this.heartbeatInterval = setInterval(() => {
            this.sendHeartbeat();
        }, 30000);
    }
    
    sendHeartbeat() {
        const taskId = this.getTaskId();
        if (!taskId) return;
        
        fetch(`/operators/workspace/${taskId}/heartbeat/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCookie('csrftoken')
            }
        })
        .catch(error => console.log('Heartbeat failed:', error));
    }
    
    setupVideoPlayer() {
        const video = document.getElementById('video-player');
        if (!video) return;
        
        const indicator = document.getElementById('timestamp-indicator');
        const timeDisplay = document.getElementById('current-time');
        
        if (indicator && timeDisplay) {
            video.addEventListener('timeupdate', () => {
                const time = video.currentTime;
                const minutes = Math.floor(time / 60);
                const seconds = (time % 60).toFixed(3);
                timeDisplay.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.padStart(6, '0')}`;
                indicator.style.display = 'block';
            });
            
            video.addEventListener('seeking', () => {
                indicator.style.display = 'block';
            });
        }
    }
    
    selectTrigger(triggerId, timestamp) {
        // Remove active class from all triggers
        document.querySelectorAll('.trigger-row').forEach(row => {
            row.classList.remove('active');
        });
        
        // Add active class to selected trigger
        const selectedRow = document.querySelector(`[data-trigger-id="${triggerId}"]`);
        if (selectedRow) {
            selectedRow.classList.add('active');
        }
        
        this.currentTriggerId = triggerId;
        
        // Load decision panel
        htmx.ajax('GET', `/operators/workspace/${this.getTaskId()}/trigger/${triggerId}/labels/`, {
            target: '#decision-panel-content'
        });
        
        // Sync video player timestamp
        this.syncVideoToTimestamp(timestamp);
    }
    
    syncVideoToTimestamp(timestamp) {
        const video = document.getElementById('video-player');
        if (!video || !timestamp) return;
        
        const targetTime = parseFloat(timestamp);
        const currentTime = video.currentTime;
        const diff = Math.abs(currentTime - targetTime);
        
        // Show warning if desynced more than threshold
        if (diff > this.desyncThreshold) {
            this.showDesyncWarning(currentTime, targetTime);
        }
        
        // Jump to timestamp
        video.currentTime = targetTime;
    }
    
    showDesyncWarning(current, target) {
        // Remove existing warnings
        document.querySelectorAll('.desync-warning').forEach(w => w.remove());
        
        const warningHtml = `
            <div class="desync-warning">
                <strong>Внимание:</strong> Время плеера (${current.toFixed(2)}с) отличается от времени триггера (${target.toFixed(2)}с)
                <button class="btn btn-sm btn-primary ms-2" onclick="workspace.syncToTrigger(${target})">
                    Синхронизировать
                </button>
            </div>
        `;
        
        const panel = document.getElementById('decision-panel-content');
        if (panel) {
            panel.insertAdjacentHTML('afterbegin', warningHtml);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                const warning = panel.querySelector('.desync-warning');
                if (warning) warning.remove();
            }, 5000);
        }
    }
    
    syncToTrigger(timestamp) {
        const video = document.getElementById('video-player');
        if (video) {
            video.currentTime = timestamp;
        }
    }
    
    submitDecision(triggerId, finalLabel, comment) {
        const data = {
            final_label: finalLabel,
            comment: comment || ''
        };
        
        fetch(`/operators/workspace/${this.getTaskId()}/trigger/${triggerId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCookie('csrftoken')
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.onTriggerProcessed(triggerId);
            } else {
                this.showError('Ошибка: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            this.showError('Произошла ошибка при отправке решения');
        });
    }
    
    showError(message) {
        // Remove existing error alerts
        document.querySelectorAll('.alert-danger').forEach(alert => alert.remove());
        
        const errorHtml = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        // Insert at the top of the main content area
        const mainContent = document.querySelector('.container-fluid');
        if (mainContent) {
            mainContent.insertAdjacentHTML('afterbegin', errorHtml);
        }
    }
    
    onTriggerProcessed(triggerId) {
        // Remove the trigger row
        const triggerRow = document.querySelector(`[data-trigger-id="${triggerId}"]`);
        if (triggerRow) {
            triggerRow.remove();
        }
        
        // Clear decision panel
        const panel = document.getElementById('decision-panel-content');
        if (panel) {
            panel.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="bi bi-check-circle display-4 text-success"></i>
                    <p class="mt-2">Триггер обработан</p>
                    <small>Выберите следующий триггер</small>
                </div>
            `;
        }
        
        this.currentTriggerId = null;
        
        // Update trigger count
        const countElement = document.querySelector('.triggers-panel h6');
        const currentCount = document.querySelectorAll('.trigger-row').length;
        if (countElement) {
            countElement.textContent = `AI Триггеры (${currentCount})`;
        }
        
        // Check if all triggers are processed
        if (currentCount === 0) {
            const triggersList = document.querySelector('.triggers-list');
            if (triggersList) {
                triggersList.innerHTML = `
                    <div class="text-center text-muted py-4">
                        <p>Все триггеры обработаны!</p>
                        <small>Можно завершать верификацию</small>
                    </div>
                `;
            }
        }
    }
    
    getTaskId() {
        // Extract task ID from current URL
        const pathParts = window.location.pathname.split('/');
        const taskIndex = pathParts.indexOf('workspace');
        if (taskIndex !== -1 && pathParts.length > taskIndex + 1) {
            return pathParts[taskIndex + 1];
        }
        return null;
    }
    
    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    cleanup() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
        }
    }
}

// Global functions for onclick handlers
function selectTrigger(triggerId, timestamp) {
    if (window.workspace) {
        window.workspace.selectTrigger(triggerId, timestamp);
    }
}

function submitDecision(triggerId, finalLabel, comment) {
    if (window.workspace) {
        window.workspace.submitDecision(triggerId, finalLabel, comment);
    }
}

function syncToTrigger(timestamp) {
    if (window.workspace) {
        window.workspace.syncToTrigger(timestamp);
    }
}

function completeVerification() {
    const decisionSummary = document.getElementById('decision_summary').value;
    
    fetch(`/operators/workspace/${window.workspace.getTaskId()}/complete/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.workspace.getCookie('csrftoken')
        },
        body: JSON.stringify({
            decision_summary: decisionSummary
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.href = data.redirect_url;
        } else {
            window.workspace.showError('Ошибка: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        window.workspace.showError('Произошла ошибка при завершении верификации');
    });
}

function clearDecisionPanel() {
    const panel = document.getElementById('decision-panel-content');
    if (panel) {
        panel.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="bi bi-hand-index display-4"></i>
                <p class="mt-2">Выберите триггер для обработки</p>
                <small>Нажмите на любой триггер слева</small>
            </div>
        `;
    }
}

// Initialize workspace when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.workspace = new OperatorWorkspace();
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (window.workspace) {
        window.workspace.cleanup();
    }
});