// static/batch_manager/js/batch_manager.js

document.addEventListener('DOMContentLoaded', function() {
    // Configuration globale Ajax
    $.ajaxSetup({
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').val()
        }
    });

    // Initialisation
    initializeEventListeners();
    updateDashboard();
    startProgressBars();
    
    // Mises à jour régulières
    setInterval(updateDashboard, 30000);
    setInterval(updateRelativeTimes, 60000);
});

// Initialisation des écouteurs d'événements
function initializeEventListeners() {
    // Gestionnaire pour les boutons toggle
    document.querySelectorAll('.toggle-batch').forEach(button => {
        button.addEventListener('click', function() {
            const jobId = this.dataset.jobId;
            toggleBatch(jobId);
        });
    });

    // Gestionnaire pour les boutons de suppression
    document.querySelectorAll('.delete-batch').forEach(button => {
        button.addEventListener('click', function() {
            const jobId = this.dataset.jobId;
            deleteBatch(jobId);
        });
    });

    // Gestionnaire pour le choix de la commande
    const commandSelect = document.querySelector('#id_command');
    const startDateField = document.querySelector('.start-date-field');

    if (commandSelect) {
        commandSelect.addEventListener('change', function() {
            startDateField.style.display = 
                this.value === 'sync_matches_from_date' ? 'block' : 'none';
        });
    }
}

// Mise à jour du tableau de bord
function updateDashboard() {
    const activeJobs = document.querySelectorAll('[data-running="true"]').length;
    document.getElementById('active-jobs-count').textContent = activeJobs;
    document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
}

// Gestion des barres de progression
function startProgressBars() {
    document.querySelectorAll('[data-running="true"]').forEach(batchElement => {
        const jobId = batchElement.dataset.jobId;
        startProgressBar(jobId);
    });
}

function startProgressBar(jobId) {
    const batchElement = document.querySelector(`#batch-${jobId}`);
    if (!batchElement) return;

    const progressBar = batchElement.querySelector('.progress-bar');
    const timeRemaining = batchElement.querySelector('.time-remaining');
    const timing = parseInt(batchElement.dataset.timing) * 60 * 1000; // en millisecondes
    const lastRun = new Date(batchElement.querySelector('.last-run').dataset.timestamp);
    
    function updateProgress() {
        if (!batchElement.dataset.running === 'true') return;

        const now = new Date();
        const elapsed = now - lastRun;
        const remaining = timing - elapsed;
        const progress = (elapsed / timing) * 100;

        if (remaining > 0) {
            progressBar.style.width = `${Math.min(progress, 100)}%`;
            timeRemaining.textContent = formatTimeRemaining(remaining);
            requestAnimationFrame(updateProgress);
        } else {
            progressBar.style.width = '100%';
            timeRemaining.textContent = 'Exécution imminente...';
        }
    }

    updateProgress();
}

// Actions sur les batchs
async function toggleBatch(jobId) {
    try {
        const response = await fetch(`/batch/toggle/${jobId}/`, {
            method: 'POST'
        });

        const data = await response.json();
        
        if (data.success) {
            updateBatchUI(jobId, data.status);
            showNotification(data.message, 'success');
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        showNotification(error.message || 'Erreur lors de la modification du batch', 'error');
    }
}

async function deleteBatch(jobId) {
    if (!confirm('Êtes-vous sûr de vouloir supprimer ce batch ?')) {
        return;
    }

    try {
        const response = await fetch(`/batch/delete/${jobId}/`, {
            method: 'POST'
        });

        const data = await response.json();
        
        if (data.success) {
            document.querySelector(`#batch-${jobId}`).remove();
            updateDashboard();
            showNotification(data.message, 'success');
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        showNotification(error.message || 'Erreur lors de la suppression du batch', 'error');
    }
}

// Fonctions utilitaires
function updateBatchUI(jobId, status) {
    const batchElement = document.querySelector(`#batch-${jobId}`);
    const button = batchElement.querySelector('.toggle-batch');
    const statusBadge = batchElement.querySelector('.status-badge');
    const progressContainer = batchElement.querySelector('.progress-container');

    if (status === 'started') {
        button.innerHTML = '<i class="fas fa-stop mr-2"></i>STOP';
        button.classList.remove('bg-green-500', 'hover:bg-green-600');
        button.classList.add('bg-red-500', 'hover:bg-red-600');
        statusBadge.textContent = 'En cours';
        statusBadge.classList.remove('bg-gray-100', 'text-gray-800');
        statusBadge.classList.add('bg-green-100', 'text-green-800');
        batchElement.dataset.running = 'true';
        progressContainer.style.display = 'block';
        startProgressBar(jobId);
    } else {
        button.innerHTML = '<i class="fas fa-play mr-2"></i>START';
        button.classList.remove('bg-red-500', 'hover:bg-red-600');
        button.classList.add('bg-green-500', 'hover:bg-green-600');
        statusBadge.textContent = 'Arrêté';
        statusBadge.classList.remove('bg-green-100', 'text-green-800');
        statusBadge.classList.add('bg-gray-100', 'text-gray-800');
        batchElement.dataset.running = 'false';
        progressContainer.style.display = 'none';
    }

    updateDashboard();
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed bottom-4 right-4 p-4 rounded-lg shadow-lg ${
        type === 'success' ? 'bg-green-500' : 
        type === 'error' ? 'bg-red-500' : 
        'bg-blue-500'
    } text-white`;
    notification.textContent = message;

    document.body.appendChild(notification);
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

function formatTimeRemaining(ms) {
    const minutes = Math.floor(ms / 60000);
    const seconds = Math.floor((ms % 60000) / 1000);
    return `${minutes}m ${seconds}s`;
}

function updateRelativeTimes() {
    document.querySelectorAll('.last-run').forEach(element => {
        const timestamp = new Date(element.dataset.timestamp);
        const now = new Date();
        const diff = now - timestamp;
        
        if (diff < 60000) {
            element.textContent = 'À l\'instant';
        } else if (diff < 3600000) {
            const minutes = Math.floor(diff / 60000);
            element.textContent = `Il y a ${minutes} minute${minutes > 1 ? 's' : ''}`;
        } else if (diff < 86400000) {
            const hours = Math.floor(diff / 3600000);
            element.textContent = `Il y a ${hours} heure${hours > 1 ? 's' : ''}`;
        } else {
            element.textContent = timestamp.toLocaleDateString();
        }
    });
}