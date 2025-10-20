// StarLogs - Enhanced UI with event timeline
// Author: Ozy311

class StarLogsApp {
    constructor() {
        this.eventSource = null;
        this.autoScroll = true;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        
        // Badges visibility state
        this.badgesVisible = true;
        
        // Event filters - initialize from saved state if available
        this.filters = {
            pve: true,
            pvp: true,
            deaths: true,
            fps_pve: true,
            fps_pvp: true,
            fps_death: true,
            disconnects: true,
            vehicle_soft: true,
            vehicle_full: true,
            corpse: true,
            suicide: true
        };
        
        // Event counters
        this.counters = {
            pve: 0,
            pvp: 0,
            deaths: 0,
            fps_pve: 0,
            fps_pvp: 0,
            fps_death: 0,
            disconnects: 0,
            vehicle_soft: 0,
            vehicle_full: 0,
            stalls: 0,
            corpse: 0,
            suicide: 0
        };
        
        this.initializeElements();
        this.loadLogPreferences(); // Load UI preferences FIRST
        this.attachEventListeners(); // Attach listeners BEFORE loading badge visibility
        this.loadBadgeVisibility(); // Load badge visibility AFTER listeners are attached
        this.initializeResizer();
        this.loadVersions();
        this.connect();
        this.updateStatus();
    }
    
    initializeElements() {
        // Status elements
        this.connectionStatus = document.getElementById('connection-status');
        this.logPath = document.getElementById('log-path');
        this.totalLines = document.getElementById('total-lines');
        this.gameStatus = document.getElementById('game-status');
        
        // Counter badges
        this.pveCount = document.getElementById('pve-count');
        this.pvpCount = document.getElementById('pvp-count');
        this.deathCount = document.getElementById('death-count');
        this.fpsPveCount = document.getElementById('fps-pve-count');
        this.fpsPvpCount = document.getElementById('fps-pvp-count');
        this.fpsDeathCount = document.getElementById('fps-death-count');
        this.suicideCount = document.getElementById('suicide-count');
        this.corpseCount = document.getElementById('corpse-count');
        this.disconnectCount = document.getElementById('disconnect-count');
        this.vehicleSoftCount = document.getElementById('vehicle-soft-count');
        this.vehicleFullCount = document.getElementById('vehicle-full-count');
        
        // Event list
        this.eventsList = document.getElementById('events-list');
        
        // Raw log output
        this.logOutput = document.getElementById('log-output');
        
        // UI controls
        this.themeToggleBtn = document.getElementById('theme-toggle');
        this.settingsBtn = document.getElementById('settings-btn');
        this.settingsMenu = document.getElementById('settings-menu');
        this.aboutModal = document.getElementById('about-modal');
        this.aboutBtn = document.getElementById('about-btn');
        this.themeSelect = document.getElementById('theme-select');
        
        // Version selector
        this.versionDropdown = document.getElementById('versionDropdown');
        this.versionSelected = document.getElementById('versionSelected');
        this.versionOptions = document.getElementById('versionOptions');
        this.activeVersion = document.getElementById('activeVersion');
        this.availableVersions = [];
        
        // Settings tabs
        this.settingsTabs = document.querySelectorAll('.tab-btn');
        this.tabContents = document.querySelectorAll('.tab-content');
        this.installationsList = document.getElementById('installations-list');
        this.addCustomPathBtn = document.getElementById('add-custom-path-btn');
        this.customPathForm = document.getElementById('custom-path-form');
        this.customPathInput = document.getElementById('custom-path-input');
        this.validatePathBtn = document.getElementById('validate-path-btn');
        this.cancelCustomPathBtn = document.getElementById('cancel-custom-path-btn');
        this.pathValidationResult = document.getElementById('path-validation-result');
        
        // General settings
        this.portInput = document.getElementById('port-input');
        this.portSaveStatus = document.getElementById('port-save-status');
        
        // Historical logs
        this.historyBtn = document.getElementById('history-btn');
        this.exportCurrentBtn = document.getElementById('export-current-btn');
        this.historyModal = document.getElementById('history-modal');
        this.historyVersionSelect = document.getElementById('history-version-select');
        this.historySortSelect = document.getElementById('history-sort-select');
        this.historyList = document.getElementById('history-list');
        this.historyCount = document.getElementById('history-count');
        this.currentHistoryFiles = []; // Store current files for sorting
        
        // Analysis modal
        this.analysisModal = document.getElementById('analysis-modal');
        this.analysisTitle = document.getElementById('analysis-title');
        this.analysisContent = document.getElementById('analysis-content');
        this.exportHtmlBtn = document.getElementById('export-html-btn');
        this.currentAnalyzedLog = null;
        
        // Resizer elements
        this.divider = document.getElementById('resize-divider');
        
        // Load saved theme
        this.loadTheme();
        
        // Controls
        this.autoScrollCheckbox = document.getElementById('auto-scroll');
        this.wrapTextCheckbox = document.getElementById('wrap-text');
        this.clearEventsBtn = document.getElementById('clear-events');
        this.clearLogBtn = document.getElementById('clear-log');
        this.reprocessBtn = document.getElementById('reprocess-log');
        
        // Load saved preferences
        this.loadLogPreferences();
    }
    
    attachEventListeners() {
        // Badge filter clicks
        document.querySelectorAll('.count-badge[data-filter]').forEach(badge => {
            badge.addEventListener('click', () => {
                const filterName = badge.dataset.filter;
                this.filters[filterName] = !this.filters[filterName];
                badge.classList.toggle('active');
                this.filterEvents();
                this.saveBadgeVisibility(); // Save changes immediately
            });
        });
        
        // Invert button
        const invertBtn = document.getElementById('invert-badges-btn');
        if (invertBtn) {
            invertBtn.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent triggering section collapse
                // Invert all badge visibility
                Object.keys(this.filters).forEach(key => {
                    this.filters[key] = !this.filters[key];
                });
                
                // Update UI
                document.querySelectorAll('.count-badge[data-filter]').forEach(badge => {
                    const filterName = badge.dataset.filter;
                    if (this.filters[filterName]) {
                        badge.classList.add('active');
                    } else {
                        badge.classList.remove('active');
                    }
                });
                
                // Refilter events and save
                this.filterEvents();
                this.saveBadgeVisibility();
            });
        }
        
        this.autoScrollCheckbox.addEventListener('change', (e) => {
            this.autoScroll = e.target.checked;
            localStorage.setItem('starlogger-auto-scroll', this.autoScroll);
        });
        
        this.wrapTextCheckbox.addEventListener('change', (e) => {
            const wrapEnabled = e.target.checked;
            if (wrapEnabled) {
                this.logOutput.classList.add('wrap-text');
            } else {
                this.logOutput.classList.remove('wrap-text');
            }
            localStorage.setItem('starlogger-wrap-text', wrapEnabled);
        });
        
        // Clear buttons
        this.clearEventsBtn.addEventListener('click', () => {
            this.eventsList.innerHTML = '<div class="empty-state">No events yet. Waiting for game activity...</div>';
            this.counters = { pve: 0, pvp: 0, deaths: 0, disconnects: 0, vehicle_soft: 0, vehicle_full: 0 };
            this.pveCount.textContent = '0 Ship PvE';
            this.pvpCount.textContent = '0 Ship PvP';
            this.deathCount.textContent = '0 Deaths';
            this.disconnectCount.textContent = '0 DC';
            if (this.vehicleSoftCount) this.vehicleSoftCount.textContent = '0 Soft';
            if (this.vehicleFullCount) this.vehicleFullCount.textContent = '0 Full';
        });
        
        this.clearLogBtn.addEventListener('click', () => {
            this.logOutput.innerHTML = '';
        });
        
        // Reprocess button
        this.reprocessBtn.addEventListener('click', async () => {
            if (confirm('Reprocess the entire game log? This will clear current events and reload all data.')) {
                try {
                    this.reprocessBtn.disabled = true;
                    this.reprocessBtn.textContent = '↻ Processing...';
                    
                    const response = await fetch('/reprocess', { method: 'POST' });
                    const result = await response.json();
                    
                    if (result.status === 'success') {
                        // Reload the page to get fresh data
                        console.log('Reprocess complete, reloading page...');
                        setTimeout(() => window.location.reload(), 1000);
                    } else {
                        alert('Failed to reprocess log: ' + result.message);
                        this.reprocessBtn.disabled = false;
                        this.reprocessBtn.textContent = '↻ Reprocess Log';
                    }
                } catch (e) {
                    console.error('Error reprocessing log:', e);
                    alert('Error reprocessing log');
                    this.reprocessBtn.disabled = false;
                    this.reprocessBtn.textContent = '↻ Reprocess Log';
                }
            }
        });
        
        // Theme toggle (moved to settings menu)
        if (this.themeToggleBtn) {
            this.themeToggleBtn.addEventListener('click', () => {
                this.toggleTheme();
            });
        }
        
        // Settings menu
        this.settingsBtn.addEventListener('click', () => {
            this.settingsMenu.classList.add('show');
            this.loadGameInstallations(); // Load installations when opening settings
            this.loadAboutInfo(); // Load about info when opening settings
            this.loadGeneralSettings(); // Load general settings
        });
        
        // Historical logs
        this.historyBtn.addEventListener('click', () => {
            this.openHistoryBrowser();
        });
        
        // Export current log
        this.exportCurrentBtn.addEventListener('click', async () => {
            try {
                const response = await fetch('/api/log_file');
                const data = await response.json();
                
                if (data.log_file) {
                    await this.exportLogHTML(data.log_file, 'Current Game Log');
                } else {
                    alert('No active game log found');
                }
            } catch (error) {
                console.error('Error exporting current log:', error);
                alert('Error exporting current log');
            }
        });
        
        this.historyVersionSelect.addEventListener('change', (e) => {
            const version = e.target.value;
            if (version) {
                this.loadHistoricalLogs(version);
            }
        });
        
        this.historySortSelect.addEventListener('change', () => {
            this.sortAndRenderHistory();
        });
        
        this.exportHtmlBtn.addEventListener('click', () => {
            this.exportCurrentLog();
        });
        
        // Settings tabs
        this.settingsTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const targetTab = tab.dataset.tab;
                this.switchTab(targetTab);
            });
        });
        
        // Custom path form
        this.addCustomPathBtn.addEventListener('click', () => {
            this.customPathForm.style.display = 'block';
            this.customPathInput.focus();
        });
        
        this.cancelCustomPathBtn.addEventListener('click', () => {
            this.customPathForm.style.display = 'none';
            this.customPathInput.value = '';
            this.pathValidationResult.style.display = 'none';
        });
        
        this.validatePathBtn.addEventListener('click', () => {
            this.validateCustomPath();
        });
        
        // About button - now handled by settings tab
        // No longer used since About is in settings
        
        // Theme select in settings
        this.themeSelect.addEventListener('change', (e) => {
            const theme = e.target.value;
            this.setTheme(theme);
        });
        
        // Port input - save on change with debounce
        let portSaveTimeout;
        this.portInput.addEventListener('change', (e) => {
            clearTimeout(portSaveTimeout);
            portSaveTimeout = setTimeout(() => {
                this.savePortSetting(parseInt(e.target.value));
            }, 500);
        });
        
        // Version dropdown toggle
        this.versionSelected.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleVersionDropdown();
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.versionDropdown.contains(e.target)) {
                this.closeVersionDropdown();
            }
        });
        
        // Close modals when clicking outside
        window.addEventListener('click', (e) => {
            if (e.target === this.settingsMenu) {
                this.settingsMenu.classList.remove('show');
            }
            if (e.target === this.aboutModal) {
                this.aboutModal.classList.remove('show');
            }
        });
        
        // New Header Icon Button Listeners
        
        // Connection Status Button (WiFi Icon)
        const connectionBtn = document.getElementById('connection-btn');
        if (connectionBtn) {
            connectionBtn.addEventListener('click', () => {
                const status = this.connectionStatus.textContent;
                alert(`Server Connection Status: ${status}`);
            });
        }
        
        // Theme Toggle Button
        const themeToggleBtn = document.getElementById('theme-toggle-btn');
        if (themeToggleBtn) {
            themeToggleBtn.addEventListener('click', () => {
                this.toggleTheme();
            });
        }
        
        // About Button
        const aboutBtn = document.getElementById('about-btn');
        if (aboutBtn) {
            aboutBtn.addEventListener('click', () => {
                this.openAboutModal();
            });
        }
        
        // Mobile Menu Toggle
        const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
        const mobileMenuFlyout = document.getElementById('mobile-menu-flyout');
        if (mobileMenuToggle && mobileMenuFlyout) {
            mobileMenuToggle.addEventListener('click', () => {
                mobileMenuFlyout.classList.toggle('show');
            });
            
            // Close menu when clicking outside
            document.addEventListener('click', (e) => {
                if (!mobileMenuToggle.contains(e.target) && !mobileMenuFlyout.contains(e.target)) {
                    mobileMenuFlyout.classList.remove('show');
                }
            });
        }
        
        // Mobile History Button
        const mobileHistoryBtn = document.getElementById('mobile-history-btn');
        if (mobileHistoryBtn) {
            mobileHistoryBtn.addEventListener('click', () => {
                if (mobileMenuFlyout) mobileMenuFlyout.classList.remove('show');
                this.openHistoryBrowser();
            });
        }
        
        // Mobile Export Button
        const mobileExportBtn = document.getElementById('mobile-export-btn');
        if (mobileExportBtn) {
            mobileExportBtn.addEventListener('click', async () => {
                if (mobileMenuFlyout) mobileMenuFlyout.classList.remove('show');
                try {
                    const response = await fetch('/api/log_file');
                    const data = await response.json();
                    
                    if (data.log_file) {
                        await this.exportLogHTML(data.log_file, 'Current Game Log');
                    } else {
                        alert('No active game log found');
                    }
                } catch (error) {
                    console.error('Error exporting current log:', error);
                    alert('Error exporting current log');
                }
            });
        }
        
        // Mobile Version Button - Show alert with version info
        const mobileVersionBtn = document.getElementById('mobile-version-btn');
        if (mobileVersionBtn) {
            mobileVersionBtn.addEventListener('click', () => {
                if (mobileMenuFlyout) mobileMenuFlyout.classList.remove('show');
                // You can expand this to show version selector later
                alert('Version switching on mobile coming soon');
            });
        }
        
        // Mobile Settings Button
        const mobileSettingsBtn = document.getElementById('mobile-settings-btn');
        if (mobileSettingsBtn) {
            mobileSettingsBtn.addEventListener('click', () => {
                if (mobileMenuFlyout) mobileMenuFlyout.classList.remove('show');
                this.settingsMenu.classList.add('show');
                this.loadGameInstallations();
                this.loadAboutInfo();
                this.loadGeneralSettings();
            });
        }
    }
    
    loadTheme() {
        const savedTheme = localStorage.getItem('starlogger-theme') || 'dark';
        this.setTheme(savedTheme);
        this.themeSelect.value = savedTheme;
    }
    
    setTheme(theme) {
        if (theme === 'light') {
            document.body.classList.add('light-mode');
            if (this.themeToggleBtn) {
                this.themeToggleBtn.querySelector('.theme-icon').textContent = '🌙';
            }
        } else {
            document.body.classList.remove('light-mode');
            if (this.themeToggleBtn) {
                this.themeToggleBtn.querySelector('.theme-icon').textContent = '☀️';
            }
        }
        localStorage.setItem('starlogger-theme', theme);
    }
    
    toggleTheme() {
        // Toggle between dark and light mode
        const html = document.documentElement;
        const currentMode = html.getAttribute('data-theme') || 'dark';
        const newMode = currentMode === 'dark' ? 'light' : 'dark';
        
        html.setAttribute('data-theme', newMode);
        localStorage.setItem('starlogger-theme', newMode);
        
        // Update theme toggle button icon and title
        const themeBtn = document.getElementById('theme-toggle-btn');
        if (themeBtn) {
            const icon = themeBtn.querySelector('i');
            if (icon) {
                if (newMode === 'light') {
                    icon.className = 'fas fa-moon';
                    themeBtn.title = 'Light Mode (click to toggle to Dark Mode)';
                } else {
                    icon.className = 'fas fa-sun';
                    themeBtn.title = 'Dark Mode (click to toggle to Light Mode)';
                }
            }
        }
        
        // Apply light mode class to body if needed
        const body = document.body;
        if (newMode === 'light') {
            body.classList.add('light-mode');
        } else {
            body.classList.remove('light-mode');
        }
    }
    
    loadLogPreferences() {
        // Load auto-scroll preference (default: true)
        const savedAutoScroll = localStorage.getItem('starlogger-auto-scroll');
        if (savedAutoScroll !== null) {
            this.autoScroll = savedAutoScroll === 'true';
            this.autoScrollCheckbox.checked = this.autoScroll;
        }
        
        // Load wrap-text preference (default: false - no wrap)
        const savedWrapText = localStorage.getItem('starlogger-wrap-text');
        if (savedWrapText !== null) {
            const wrapEnabled = savedWrapText === 'true';
            this.wrapTextCheckbox.checked = wrapEnabled;
            if (wrapEnabled) {
                this.logOutput.classList.add('wrap-text');
            } else {
                this.logOutput.classList.remove('wrap-text');
            }
        }
        
        // Load badges visibility preference (default: true - visible)
        // Use a small delay to ensure DOM elements are ready
        setTimeout(() => {
            const savedBadgesVisible = localStorage.getItem('starlogger-badges-visible');
            if (savedBadgesVisible === 'false') {
                this.badgesVisible = false;
                const badgesContent = document.getElementById('badges-content');
                const badgesIcon = document.querySelector('.badges-toggle-icon');
                if (badgesContent && badgesIcon) {
                    badgesContent.classList.add('collapsed');
                    badgesIcon.classList.add('collapsed');
                    badgesIcon.textContent = '▶';
                    console.log('[DEBUG] Badges collapsed state restored from localStorage');
                }
            }
        }, 100);
    }
    
    // Version Management
    async loadVersions() {
        try {
            const response = await fetch('/api/versions');
            const data = await response.json();
            this.availableVersions = data.installations || [];
            this.populateVersionDropdown();
            
            // Find and display active version (currently being monitored)
            let activeInstall = this.availableVersions.find(v => v.is_active);
            
            // Fallback: match by log path if current_log_path is provided
            if (!activeInstall && data.current_log_path) {
                activeInstall = this.availableVersions.find(v => v.log_path === data.current_log_path);
            }
            
            // Fallback: if no match, use first version with has_log=true
            if (!activeInstall) {
                activeInstall = this.availableVersions.find(v => v.has_log);
            }
            
            // Last resort: just use first version
            if (!activeInstall && this.availableVersions.length > 0) {
                activeInstall = this.availableVersions[0];
            }
            
            if (activeInstall) {
                this.activeVersion.textContent = activeInstall.display_name;
            }
        } catch (error) {
            console.error('Failed to load versions:', error);
            this.activeVersion.textContent = 'Error loading versions';
        }
    }
    
    populateVersionDropdown() {
        this.versionOptions.innerHTML = '';
        
        this.availableVersions.forEach(version => {
            const option = document.createElement('button');
            option.className = 'version-option';
            option.dataset.version = version.version;
            
            // Add active class if currently being monitored
            if (version.is_active) {
                option.classList.add('active');
            }
            
            option.innerHTML = `
                <span class="version-bullet">●</span>
                <div style="flex: 1;">
                    <div class="version-option-name">${version.display_name}</div>
                    <div class="version-option-path">${version.path}</div>
                </div>
            `;
            
            option.addEventListener('click', () => {
                this.switchVersion(version.version, version.display_name);
            });
            
            this.versionOptions.appendChild(option);
        });
    }
    
    toggleVersionDropdown() {
        const isOpen = this.versionOptions.style.display === 'block';
        if (isOpen) {
            this.closeVersionDropdown();
        } else {
            this.openVersionDropdown();
        }
    }
    
    openVersionDropdown() {
        this.versionOptions.style.display = 'block';
        this.versionDropdown.classList.add('open');
    }
    
    closeVersionDropdown() {
        this.versionOptions.style.display = 'none';
        this.versionDropdown.classList.remove('open');
    }
    
    async switchVersion(version, displayName) {
        this.closeVersionDropdown();
        
        // Show switching message
        this.activeVersion.textContent = `Switching to ${displayName}...`;
        this.showMessage(`Switching to ${displayName}...`, 'info');
        
        try {
            const response = await fetch('/api/switch_version', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ version: version })
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                // Update display
                this.activeVersion.textContent = displayName;
                this.showMessage(`Switched to ${displayName}`, 'success');
                
                // Clear UI
                this.clearAll();
                
                // Reconnect SSE to new version
                if (this.eventSource) {
                    this.eventSource.close();
                }
                setTimeout(() => {
                    this.connect();
                }, 1000);
                
                // Update dropdown active state
                this.loadVersions();
            } else {
                throw new Error(result.message || 'Switch failed');
            }
        } catch (error) {
            console.error('Failed to switch version:', error);
            this.showMessage(`Failed to switch: ${error.message}`, 'error');
            this.loadVersions(); // Reload to reset display
        }
    }
    
    showMessage(message, type = 'info') {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--bg-secondary);
            color: var(--text-primary);
            padding: 12px 20px;
            border-radius: 6px;
            border: 1px solid ${type === 'success' ? 'var(--accent-green)' : type === 'error' ? 'var(--accent-red)' : 'var(--accent-blue)'};
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease-in';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    clearAll() {
        // Clear events
        this.eventsList.innerHTML = '<div class="empty-state">No events yet. Waiting for game activity...</div>';
        
        // Clear log output
        this.logOutput.innerHTML = '';
        
        // Reset counters
        this.counters = { pve: 0, pvp: 0, deaths: 0, disconnects: 0, vehicle_soft: 0, vehicle_full: 0 };
        this.pveCount.textContent = '0 Ship PvE';
        this.pvpCount.textContent = '0 Ship PvP';
        this.deathCount.textContent = '0 Deaths';
        this.disconnectCount.textContent = '0 Stalls';
        if (this.vehicleSoftCount) this.vehicleSoftCount.textContent = '0 Soft';
        if (this.vehicleFullCount) this.vehicleFullCount.textContent = '0 Full';
    }
    
    async loadAboutInfo() {
        try {
            const response = await fetch('/about');
            const data = await response.json();
            
            // Update inline About tab content (in settings)
            document.getElementById('about-version-inline').textContent = `v${data.version}`;
            document.getElementById('about-description-inline').textContent = data.description;
            
            const featuresListInline = document.getElementById('about-features-inline');
            featuresListInline.innerHTML = '';
            data.features.forEach(feature => {
                const li = document.createElement('li');
                li.textContent = feature;
                featuresListInline.appendChild(li);
            });
            
            // Also update old modal (if still present for backward compatibility)
            const versionEl = document.getElementById('about-version');
            const descEl = document.getElementById('about-description');
            const featuresEl = document.getElementById('about-features');
            
            if (versionEl) versionEl.textContent = `v${data.version}`;
            if (descEl) descEl.textContent = data.description;
            if (featuresEl) {
                featuresEl.innerHTML = '';
                data.features.forEach(feature => {
                    const li = document.createElement('li');
                    li.textContent = feature;
                    featuresEl.appendChild(li);
                });
            }
        } catch (e) {
            console.error('Error loading about info:', e);
        }
    }
    
    initializeResizer() {
        if (!this.divider) return;
        
        // Setup resizable divider (flexbox-based)
        let isDragging = false;
        let startY = 0;
        let startEventsFlex = 1;
        let startLogsFlex = 1;
        let containerHeight = 0;
        
        const eventsSection = document.querySelector('.summary-section');
        const logsSection = document.querySelector('.log-section');
        
        // Load saved flex values
        const savedEventsFlex = localStorage.getItem('starlogger-events-flex');
        const savedLogsFlex = localStorage.getItem('starlogger-logs-flex');
        
        if (savedEventsFlex && savedLogsFlex) {
            eventsSection.style.flex = `${savedEventsFlex} 1 0`;
            logsSection.style.flex = `${savedLogsFlex} 1 0`;
        }
        
        this.divider.addEventListener('mousedown', (e) => {
            isDragging = true;
            startY = e.clientY;
            
            // Get current flex values
            const eventsStyle = window.getComputedStyle(eventsSection);
            const logsStyle = window.getComputedStyle(logsSection);
            startEventsFlex = parseFloat(eventsStyle.flexGrow) || 1;
            startLogsFlex = parseFloat(logsStyle.flexGrow) || 1;
            
            // Calculate total available height
            const container = document.querySelector('.container');
            const header = document.querySelector('header');
            const dividerHeight = this.divider.offsetHeight;
            containerHeight = container.clientHeight - header.offsetHeight - dividerHeight - 30; // 30 for padding
            
            this.divider.classList.add('dragging');
            document.body.style.cursor = 'ns-resize';
            document.body.style.userSelect = 'none';
            
            e.preventDefault();
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            
            const deltaY = e.clientY - startY;
            const deltaRatio = deltaY / containerHeight;
            
            // Adjust flex values based on mouse movement
            let newEventsFlex = Math.max(0.2, startEventsFlex + deltaRatio);
            let newLogsFlex = Math.max(0.2, startLogsFlex - deltaRatio);
            
            // Ensure minimum sizes
            if (newEventsFlex < 0.2) {
                newEventsFlex = 0.2;
                newLogsFlex = startEventsFlex + startLogsFlex - 0.2;
            }
            if (newLogsFlex < 0.2) {
                newLogsFlex = 0.2;
                newEventsFlex = startEventsFlex + startLogsFlex - 0.2;
            }
            
            eventsSection.style.flex = `${newEventsFlex} 1 0`;
            logsSection.style.flex = `${newLogsFlex} 1 0`;
            
            e.preventDefault();
        });
        
        document.addEventListener('mouseup', () => {
            if (isDragging) {
                isDragging = false;
                this.divider.classList.remove('dragging');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                
                // Save flex values to localStorage
                const eventsStyle = window.getComputedStyle(eventsSection);
                const logsStyle = window.getComputedStyle(logsSection);
                localStorage.setItem('starlogger-events-flex', eventsStyle.flexGrow);
                localStorage.setItem('starlogger-logs-flex', logsStyle.flexGrow);
            }
        });
    }
    
    connect() {
        if (this.eventSource) {
            this.eventSource.close();
        }
        
        this.connectionStatus.textContent = 'Connecting...';
        this.connectionStatus.className = 'status-value';
        
        this.eventSource = new EventSource('/events');
        
        this.eventSource.onopen = () => {
            console.log('SSE connection opened');
            this.connectionStatus.textContent = 'Connected';
            this.connectionStatus.className = 'status-value connected';
            this.reconnectAttempts = 0;
        };
        
        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (e) {
                console.error('Error parsing message:', e);
            }
        };
        
        this.eventSource.onerror = () => {
            console.error('SSE connection error');
            this.connectionStatus.textContent = 'Disconnected';
            this.connectionStatus.className = 'status-value disconnected';
            
            this.eventSource.close();
            
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
                console.log(`Reconnecting in ${delay/1000}s (attempt ${this.reconnectAttempts})`);
                setTimeout(() => this.connect(), delay);
            }
        };
    }
    
    handleMessage(data) {
        // Debug: Track message types received
        if (!this.messageStats) {
            this.messageStats = { log_line: 0, event: 0, separator: 0, clear_all: 0, other: 0 };
        }
        
        if (data.type === 'log_line') {
            this.messageStats.log_line++;
            this.addLogLine(data.line, data.has_event);
        } else if (data.type === 'event') {
            this.messageStats.event++;
            // Debug: Log first few events
            if (this.messageStats.event <= 5) {
                console.log('[DEBUG] Received event:', data.event.type, data.event);
            }
            this.addEvent(data.event);
        } else if (data.type === 'separator') {
            this.messageStats.separator++;
            console.log('[DEBUG] Separator received. Stats:', this.messageStats);
            this.addSeparator(data.message);
        } else if (data.type === 'clear_all') {
            this.messageStats.clear_all++;
            // Clear UI for reprocessing
            this.eventsList.innerHTML = '<div class="empty-state">Reprocessing...</div>';
            this.logOutput.innerHTML = '';
            this.counters = { pve: 0, pvp: 0, deaths: 0, fps_pve: 0, fps_pvp: 0, fps_death: 0, disconnects: 0, vehicle_soft: 0, vehicle_full: 0, stalls: 0, corpse: 0 };
            this.pveCount.textContent = '0 Ship PvE';
            this.pvpCount.textContent = '0 Ship PvP';
            this.deathCount.textContent = '0 Deaths';
            if (this.fpsPveCount) this.fpsPveCount.textContent = '0 FPS PvE';
            if (this.fpsPvpCount) this.fpsPvpCount.textContent = '0 FPS PvP';
            if (this.fpsDeathCount) this.fpsDeathCount.textContent = '0 FPS Death';
            this.disconnectCount.textContent = '0 DC';
            if (this.vehicleSoftCount) this.vehicleSoftCount.textContent = '0 Soft';
            if (this.vehicleFullCount) this.vehicleFullCount.textContent = '0 Full';
        } else {
            this.messageStats.other++;
            console.warn('[DEBUG] Unknown message type:', data.type, data);
        }
    }
    
    addSeparator(message) {
        // Only add separator to raw log feed, event summary doesn't need it repeated
        const logSeparator = document.createElement('div');
        logSeparator.className = 'log-separator';
        logSeparator.textContent = message;
        this.logOutput.appendChild(logSeparator);
        
        if (this.autoScroll) {
            this.logOutput.scrollTop = this.logOutput.scrollHeight;
        }
    }
    
    addEvent(event) {
        // Debug: Log if event is missing critical data
        if (!event || !event.type) {
            console.error('[DEBUG] Invalid event received:', event);
            return;
        }
        
        // Remove empty state if present
        const emptyState = this.eventsList.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
            console.log('[DEBUG] Removed empty state, first event received');
        }
        
        // Increment counters
        if (event.type === 'pve_kill') {
            this.counters.pve++;
            this.pveCount.textContent = `${this.counters.pve} Ship PvE`;
        } else if (event.type === 'pvp_kill') {
            this.counters.pvp++;
            this.pvpCount.textContent = `${this.counters.pvp} Ship PvP`;
        } else if (event.type === 'death') {
            this.counters.deaths++;
            this.deathCount.textContent = `${this.counters.deaths} Deaths`;
        } else if (event.type === 'fps_pve_kill') {
            this.counters.fps_pve++;
            if (this.fpsPveCount) this.fpsPveCount.textContent = `${this.counters.fps_pve} FPS PvE`;
        } else if (event.type === 'fps_pvp_kill') {
            this.counters.fps_pvp++;
            if (this.fpsPvpCount) this.fpsPvpCount.textContent = `${this.counters.fps_pvp} FPS PvP`;
        } else if (event.type === 'fps_death') {
            this.counters.fps_death++;
            if (this.fpsDeathCount) this.fpsDeathCount.textContent = `${this.counters.fps_death} FPS Death`;
        } else if (event.type === 'disconnect' || event.type === 'actor_stall') {
            this.counters.disconnects++;
            this.disconnectCount.textContent = `${this.counters.disconnects} Stalls`;
        } else if (event.type === 'vehicle_destroy_soft') {
            this.counters.vehicle_soft++;
            if (this.vehicleSoftCount) this.vehicleSoftCount.textContent = `${this.counters.vehicle_soft} Soft`;
        } else if (event.type === 'vehicle_destroy_full') {
            this.counters.vehicle_full++;
            if (this.vehicleFullCount) this.vehicleFullCount.textContent = `${this.counters.vehicle_full} Full`;
        }
        
        // Create event element
        const eventDiv = document.createElement('div');
        eventDiv.className = `event-item ${event.type}`;
        eventDiv.dataset.type = event.type;
        
        // Format timestamp
        const time = event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : 'Unknown';
        
        // Format summary based on event type
        let typeLabel = '';
        let typeBadge = '';
        let summary = '';
        let details = '';
        
        if (event.type === 'pve_kill') {
            typeLabel = 'Ship PvE';
            typeBadge = 'pve';
            const killer = event.details?.killer || 'Unknown';
            const victim = event.details?.victim || 'Unknown';
            const weapon = event.details?.weapon || 'Unknown weapon';
            summary = `<strong>${killer}</strong> killed <strong>${victim}</strong>`;
            details = `Weapon: ${this.formatWeaponName(weapon)}`;
        } else if (event.type === 'pvp_kill') {
            typeLabel = 'Ship PvP';
            typeBadge = 'pvp';
            const killer = event.details?.killer || 'Unknown';
            const victim = event.details?.victim || 'Unknown';
            const weapon = event.details?.weapon || 'Unknown weapon';
            summary = `<strong>${killer}</strong> killed <strong>${victim}</strong>`;
            details = `Weapon: ${this.formatWeaponName(weapon)}`;
        } else if (event.type === 'fps_pve_kill') {
            typeLabel = 'FPS PvE';
            typeBadge = 'fps-pve';
            const killer = event.details?.killer || 'Unknown';
            const victim = event.details?.victim || 'Unknown';
            const weapon = event.details?.weapon || 'Unknown weapon';
            summary = `🔫 <strong>${killer}</strong> killed <strong>${victim}</strong>`;
            details = `Weapon: ${this.formatWeaponName(weapon)}`;
        } else if (event.type === 'fps_pvp_kill') {
            typeLabel = 'FPS PvP';
            typeBadge = 'fps-pvp';
            const killer = event.details?.killer || 'Unknown';
            const victim = event.details?.victim || 'Unknown';
            const weapon = event.details?.weapon || 'Unknown weapon';
            summary = `🔫 <strong>${killer}</strong> killed <strong>${victim}</strong>`;
            details = `Weapon: ${this.formatWeaponName(weapon)}`;
        } else if (event.type === 'death') {
            typeLabel = 'Death';
            typeBadge = 'death';
            const killer = event.details?.killer || 'Unknown';
            const victim = event.details?.victim || 'You';
            summary = `<strong>${victim}</strong> was killed by <strong>${killer}</strong>`;
            details = event.details?.damage_type ? `Cause: ${event.details.damage_type}` : '';
        } else if (event.type === 'fps_death') {
            typeLabel = 'FPS Death';
            typeBadge = 'fps-death';
            const killer = event.details?.killer || 'Unknown';
            const victim = event.details?.victim || 'You';
            summary = `💀 <strong>${victim}</strong> was killed by <strong>${killer}</strong>`;
            details = event.details?.weapon ? `Weapon: ${this.formatWeaponName(event.details.weapon)}` : '';
        } else if (event.type === 'vehicle_destroy_soft') {
            typeLabel = 'Soft Death';
            typeBadge = 'vehicle-soft';
            const shipName = event.details?.ship_name || 'Unknown Ship';
            const attacker = event.details?.attacker || 'Unknown';
            const damageType = event.details?.damage_type || 'Unknown';
            const crewCount = event.details?.crew_count || 0;
            const crewNames = event.details?.crew_names || [];
            summary = `<strong>${shipName}</strong> disabled by <strong>${attacker}</strong>`;
            if (crewCount > 0) {
                summary += ` <span class="crew-indicator clickable" data-crew-count="${crewCount}" data-crew-names='${JSON.stringify(crewNames)}'>(+${crewCount} crew)</span>`;
            }
            details = damageType ? `Damage Type: ${damageType}` : '';
        } else if (event.type === 'vehicle_destroy_full') {
            typeLabel = 'Destroyed';
            typeBadge = 'vehicle-full';
            const shipName = event.details?.ship_name || 'Unknown Ship';
            const attacker = event.details?.attacker || 'Unknown';
            const damageType = event.details?.damage_type || 'Unknown';
            const crewCount = event.details?.crew_count || 0;
            const crewNames = event.details?.crew_names || [];
            summary = `<strong>${shipName}</strong> destroyed by <strong>${attacker}</strong>`;
            if (crewCount > 0) {
                summary += ` <span class="crew-indicator clickable" data-crew-count="${crewCount}" data-crew-names='${JSON.stringify(crewNames)}'>(+${crewCount} crew)</span>`;
            }
            details = damageType ? `Damage Type: ${damageType}` : '';
        } else if (event.type === 'disconnect') {
            typeLabel = 'Disconnect';
            typeBadge = 'dc';
            summary = 'Client disconnected';
            details = event.raw_line?.substring(0, 100) || '';
        } else if (event.type === 'actor_stall') {
            typeLabel = 'Actor Stall';
            typeBadge = 'stall';
            const player = event.details?.player || 'Unknown';
            const stallType = event.details?.stall_type || 'unknown';
            const length = event.details?.length || 0;
            summary = `<strong>${player}</strong> stalled`;
            details = `Type: ${stallType}, Duration: ${length}s`;
            this.counters.stalls++;
            if (this.disconnectCount) {
                this.disconnectCount.textContent = `${this.counters.stalls} Stalls`;
            }
        } else if (event.type === 'suicide') {
            typeLabel = 'Suicide';
            typeBadge = 'suicide';
            const victim = event.details?.victim || 'Unknown';
            const damageType = event.details?.damage_type || 'Unknown';
            summary = `💀 <strong>${victim}</strong> killed themselves`;
            details = `Damage Type: ${damageType}`;
            this.counters.suicide++;
            if (this.suicideCount) {
                this.suicideCount.textContent = `${this.counters.suicide} Suicides`;
            }
        } else if (event.type === 'corpse') {
            typeLabel = 'Corpse 💀';
            typeBadge = 'corpse';
            const player = event.details?.player || 'Unknown';
            const status = event.details?.status || '';
            summary = `<strong>${player}</strong> became a corpse`;
            details = status;
            this.counters.corpse++;
            if (this.corpseCount) {
                this.corpseCount.textContent = `${this.counters.corpse} Corpses`;
            }
        }
        
        // Build expanded details section with rich information
        let expandedDetails = '';
        if (event.details) {
            const parts = [];
            
            // Ship/Location info (highlighted)
            if (event.details.ship) {
                parts.push(`<span class="detail-highlight">📍 ${event.details.ship}</span>`);
            } else if (event.details.zone) {
                parts.push(`<span class="detail-muted">Zone: ${this.formatZoneName(event.details.zone)}</span>`);
            }
            
            // Weapon details
            if (event.details.weapon) {
                let weaponText = `🎯 ${this.formatWeaponName(event.details.weapon)}`;
                if (event.details.weapon_class && event.details.weapon_class !== 'unknown') {
                    weaponText += ` <span class="detail-muted">(${event.details.weapon_class})</span>`;
                }
                parts.push(weaponText);
            }
            
            // Damage type
            if (event.details.damage_type) {
                parts.push(`💥 ${event.details.damage_type}`);
            }
            
            // Direction/Distance info
            if (event.details.direction) {
                const dir = event.details.direction;
                const distance = Math.sqrt(dir.x * dir.x + dir.y * dir.y + dir.z * dir.z);
                if (distance > 0.01) {
                    // Calculate primary direction
                    const absX = Math.abs(dir.x);
                    const absY = Math.abs(dir.y);
                    const absZ = Math.abs(dir.z);
                    let dirText = '';
                    
                    if (absX > absY && absX > absZ) {
                        dirText = dir.x > 0 ? 'from Right' : 'from Left';
                    } else if (absY > absX && absY > absZ) {
                        dirText = dir.y > 0 ? 'from Above' : 'from Below';
                    } else if (absZ > 0) {
                        dirText = dir.z > 0 ? 'from Front' : 'from Behind';
                    }
                    
                    if (dirText) {
                        parts.push(`<span class="detail-direction">🧭 ${dirText}</span>`);
                    }
                }
            }
            
            // IDs (only if we have other info to show)
            if (parts.length > 0) {
                if (event.details.victim_id) {
                    parts.push(`<span class="detail-muted">Victim ID: ${event.details.victim_id}</span>`);
                }
                if (event.details.killer_id) {
                    parts.push(`<span class="detail-muted">Killer ID: ${event.details.killer_id}</span>`);
                }
            }
            
            if (parts.length > 0) {
                expandedDetails = parts.join(' <span class="detail-separator">•</span> ');
            }
        }
        
        eventDiv.innerHTML = `
            <span class="event-time">${time}</span>
            <span class="event-type ${typeBadge}">${typeLabel}</span>
            <div class="event-summary">
                ${summary}
                ${details ? `<div class="event-details">${details}</div>` : ''}
                ${expandedDetails ? `<div class="event-expanded hidden">${expandedDetails}</div>` : ''}
            </div>
            ${expandedDetails ? '<span class="event-expand-btn">▼</span>' : ''}
        `;
        
        // Add click handler to toggle expanded details
        if (expandedDetails) {
            const expandBtn = eventDiv.querySelector('.event-expand-btn');
            const expandedSection = eventDiv.querySelector('.event-expanded');
            expandBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                expandedSection.classList.toggle('hidden');
                expandBtn.textContent = expandedSection.classList.contains('hidden') ? '▼' : '▲';
            });
        }
        
        // Add click handler for crew indicator expansion
        const crewIndicator = eventDiv.querySelector('.crew-indicator.clickable');
        if (crewIndicator) {
            crewIndicator.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleCrewDetails(crewIndicator, eventDiv);
            });
        }
        
        // Insert at top (newest first)
        this.eventsList.insertBefore(eventDiv, this.eventsList.firstChild);
        
        // Apply filters
        this.applyFilterToEvent(eventDiv);
        
        // Limit events list size
        this.trimEventsList();
        
        // Auto-scroll to top to show newest event (if enabled)
        if (this.autoScroll) {
            this.eventsList.scrollTop = 0;
        }
    }
    
    formatWeaponName(weapon) {
        // Simplify weapon names for readability
        if (!weapon || weapon === 'unknown') return 'Unknown';
        
        // Extract readable part
        const parts = weapon.split('_');
        if (parts.length > 2) {
            return parts.slice(0, 3).join(' ');
        }
        return weapon;
    }
    
    formatZoneName(zone) {
        // Simplify zone names for readability
        if (!zone) return 'Unknown';
        
        // Remove long numeric IDs
        const cleaned = zone.replace(/_\d{10,}/g, '');
        
        // Split by underscores and take first few parts
        const parts = cleaned.split('_');
        if (parts.length > 3) {
            return parts.slice(0, 3).join(' ');
        }
        return cleaned.replace(/_/g, ' ');
    }
    
    getBadgeClassForDamageType(damageType) {
        // Return badge class based on damage type
        const type = (damageType || '').toLowerCase();
        switch (type) {
            case 'combat':
                return 'vehicle-combat';
            case 'collision':
                return 'vehicle-collision';
            case 'selfdestruct':
                return 'vehicle-selfdestruct';
            case 'gamerules':
                return 'vehicle-gamerules';
            default:
                return 'vehicle-default';
        }
    }
    
    toggleCrewDetails(crewIndicator, eventDiv) {
        // Check if crew list already exists
        let crewList = eventDiv.querySelector('.crew-list');
        
        if (crewList) {
            // Toggle visibility
            crewList.classList.toggle('hidden');
            const isHidden = crewList.classList.contains('hidden');
            crewIndicator.textContent = `(${isHidden ? '+' : '−'}${crewIndicator.dataset.crewCount} crew)`;
        } else {
            // Create crew list
            try {
                const crewNames = JSON.parse(crewIndicator.dataset.crewNames || '[]');
                if (crewNames.length > 0) {
                    crewList = document.createElement('div');
                    crewList.className = 'crew-list';
                    crewList.innerHTML = crewNames.map(name => 
                        `<div class="crew-member">👤 ${name}</div>`
                    ).join('');
                    
                    // Insert after the event summary
                    const summary = eventDiv.querySelector('.event-summary');
                    summary.appendChild(crewList);
                    
                    // Update indicator text
                    crewIndicator.textContent = `(−${crewIndicator.dataset.crewCount} crew)`;
                }
            } catch (e) {
                console.error('Failed to parse crew names:', e);
            }
        }
    }
    
    applyFilterToEvent(eventDiv) {
        const type = eventDiv.dataset.type;
        let show = false;
        
        if (type === 'pve_kill') show = this.filters.pve;
        else if (type === 'pvp_kill') show = this.filters.pvp;
        else if (type === 'death') show = this.filters.deaths;
        else if (type === 'fps_pve_kill') show = this.filters.fps_pve;
        else if (type === 'fps_pvp_kill') show = this.filters.fps_pvp;
        else if (type === 'fps_death') show = this.filters.fps_death;
        else if (type === 'suicide') show = this.filters.suicide;
        else if (type === 'corpse') show = this.filters.corpse;
        else if (type === 'disconnect' || type === 'actor_stall') show = this.filters.disconnects;
        else if (type === 'vehicle_destroy_soft') show = this.filters.vehicle_soft;
        else if (type === 'vehicle_destroy_full') show = this.filters.vehicle_full;
        
        eventDiv.style.display = show ? 'flex' : 'none';
    }
    
    filterEvents() {
        const events = this.eventsList.querySelectorAll('.event-item');
        events.forEach(event => this.applyFilterToEvent(event));
    }
    
    trimEventsList() {
        const maxEvents = 500;
        const events = this.eventsList.querySelectorAll('.event-item');
        if (events.length > maxEvents) {
            for (let i = maxEvents; i < events.length; i++) {
                events[i].remove();
            }
        }
    }
    
    addLogLine(line, hasEvent) {
        const div = document.createElement('div');
        div.className = hasEvent ? 'log-line has-event' : 'log-line';
        div.textContent = line;
        
        this.logOutput.appendChild(div);
        this.trimLogOutput();
        
        if (this.autoScroll) {
            this.logOutput.scrollTop = this.logOutput.scrollHeight;
        }
    }
    
    trimLogOutput() {
        const maxLines = 1000;
        while (this.logOutput.children.length > maxLines) {
            this.logOutput.removeChild(this.logOutput.firstChild);
        }
    }
    
    async updateStatus() {
        try {
            const response = await fetch('/status');
            const data = await response.json();
            
            this.totalLines.textContent = data.total_lines || 0;
            
            if (data.log_path) {
                this.logPath.textContent = data.log_path;
            }
            
            // Update game status
            if (data.game && data.game.running) {
                this.gameStatus.textContent = `Running (PID: ${data.game.pid})`;
                this.gameStatus.style.color = '#4ade80'; // Green
            } else {
                this.gameStatus.textContent = 'Not Running';
                this.gameStatus.style.color = '#fbbf24'; // Yellow
            }
        } catch (e) {
            console.error('Error fetching status:', e);
        }
        
        setTimeout(() => this.updateStatus(), 2000);
    }
    
    // Settings Tabs Methods
    switchTab(tabName) {
        // Update tab buttons
        this.settingsTabs.forEach(tab => {
            if (tab.dataset.tab === tabName) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });
        
        // Update tab content
        this.tabContents.forEach(content => {
            if (content.id === `${tabName}-tab`) {
                content.classList.add('active');
            } else {
                content.classList.remove('active');
            }
        });
    }
    
    async loadGameInstallations() {
        try {
            const response = await fetch('/api/versions');
            const data = await response.json();
            const installations = data.installations || [];
            
            if (installations.length === 0) {
                this.installationsList.innerHTML = '<div class="loading-state">No installations found</div>';
                return;
            }
            
            this.installationsList.innerHTML = '';
            installations.forEach(install => {
                const card = this.renderInstallationCard(install);
                this.installationsList.appendChild(card);
            });
        } catch (error) {
            console.error('Failed to load installations:', error);
            this.installationsList.innerHTML = '<div class="loading-state">Error loading installations</div>';
        }
    }
    
    renderInstallationCard(install) {
        const card = document.createElement('div');
        card.className = `installation-card ${install.is_active ? 'active' : ''}`;
        
        const hasLog = install.has_log ? '✓' : '✗';
        const logStatus = install.has_log ? 'Available' : 'Not Found';
        
        card.innerHTML = `
            <div class="card-header">
                <span class="card-title">${install.display_name}</span>
                ${install.is_active ? '<span class="card-badge monitoring">Currently Monitoring</span>' : ''}
                ${install.auto_detected ? '<span class="card-badge">Auto-Detected</span>' : '<span class="card-badge">Custom</span>'}
            </div>
            <div class="card-body">
                <div class="card-info"><strong>Version:</strong> ${install.version_string || 'Unknown'}</div>
                <div class="card-info"><strong>Build:</strong> ${install.build || 'Unknown'}</div>
                <div class="card-info"><strong>Branch:</strong> ${install.branch || 'Unknown'}</div>
                <div class="card-info"><strong>Log:</strong> ${hasLog} ${logStatus}</div>
                <div class="card-path"><strong>Path:</strong> ${install.path}</div>
            </div>
            <div class="card-actions">
                ${!install.is_active && install.has_log ? 
                    `<button class="btn-primary btn-monitor" onclick="app.switchToInstallation('${install.version}', '${install.display_name}')">Monitor This</button>` : 
                    ''}
                ${!install.auto_detected ? 
                    `<button class="btn-secondary btn-remove" onclick="app.removeCustomPath('${install.version}')">Remove</button>` : 
                    ''}
            </div>
        `;
        
        return card;
    }
    
    async switchToInstallation(version, displayName) {
        const confirmed = confirm(`Switch monitoring to ${displayName}?\n\nThis will restart the log monitor with the new version.`);
        
        if (!confirmed) return;
        
        try {
            await this.switchVersion(version, displayName);
            this.settingsMenu.classList.remove('show');
            this.showMessage(`Switched to ${displayName}`, 'success');
        } catch (error) {
            this.showMessage(`Failed to switch: ${error.message}`, 'error');
        }
    }
    
    async validateCustomPath() {
        const path = this.customPathInput.value.trim();
        
        if (!path) {
            this.showValidationResult('Please enter a path', 'error');
            return;
        }
        
        this.validatePathBtn.disabled = true;
        this.validatePathBtn.textContent = 'Validating...';
        
        try {
            const response = await fetch('/api/validate_path', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ path: path })
            });
            
            const result = await response.json();
            
            if (result.valid) {
                this.showValidationResult(`✓ Valid installation found: ${result.version || 'Unknown Version'}`, 'success');
                // Optionally add the path and reload installations
                setTimeout(() => {
                    this.customPathForm.style.display = 'none';
                    this.customPathInput.value = '';
                    this.loadGameInstallations();
                }, 2000);
            } else {
                this.showValidationResult(`✗ ${result.message || 'Invalid path'}`, 'error');
            }
        } catch (error) {
            this.showValidationResult('✗ Error validating path', 'error');
        } finally {
            this.validatePathBtn.disabled = false;
            this.validatePathBtn.textContent = 'Validate Path';
        }
    }
    
    showValidationResult(message, type) {
        this.pathValidationResult.textContent = message;
        this.pathValidationResult.className = `validation-result ${type}`;
        this.pathValidationResult.style.display = 'block';
    }
    
    async removeCustomPath(version) {
        const confirmed = confirm(`Remove custom installation "${version}"?`);
        
        if (!confirmed) return;
        
        try {
            const response = await fetch('/api/remove_custom_path', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ version: version })
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                this.showMessage(`Removed ${version}`, 'success');
                this.loadGameInstallations();
            } else {
                this.showMessage(`Failed to remove: ${result.message}`, 'error');
            }
        } catch (error) {
            this.showMessage(`Error: ${error.message}`, 'error');
        }
    }
    
    async loadGeneralSettings() {
        try {
            const response = await fetch('/api/config');
            const data = await response.json();
            
            if (data.web_port) {
                this.portInput.value = data.web_port;
            }
        } catch (error) {
            console.error('Failed to load settings:', error);
        }
    }
    
    async savePortSetting(port) {
        if (port < 1024 || port > 65535) {
            this.portSaveStatus.textContent = '✗ Port must be between 1024 and 65535';
            this.portSaveStatus.className = 'validation-result error';
            this.portSaveStatus.style.display = 'block';
            return;
        }
        
        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ web_port: port })
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                this.portSaveStatus.textContent = '✓ Saved! Restart StarLogs to apply changes.';
                this.portSaveStatus.className = 'validation-result success';
                this.portSaveStatus.style.display = 'block';
                
                setTimeout(() => {
                    this.portSaveStatus.style.display = 'none';
                }, 5000);
            } else {
                throw new Error(result.message || 'Failed to save');
            }
        } catch (error) {
            this.portSaveStatus.textContent = `✗ Error: ${error.message}`;
            this.portSaveStatus.className = 'validation-result error';
            this.portSaveStatus.style.display = 'block';
        }
    }
    
    // Historical Logs Methods
    async openHistoryBrowser() {
        this.historyModal.classList.add('show');
        
        // Load versions for dropdown
        try {
            const response = await fetch('/api/versions');
            const data = await response.json();
            const installations = data.installations || [];
            
            this.historyVersionSelect.innerHTML = '<option value="">Select environment...</option>';
            installations.forEach(install => {
                const option = document.createElement('option');
                option.value = install.version;
                option.textContent = install.display_name;
                this.historyVersionSelect.appendChild(option);
            });
            
            // Auto-select active version
            const activeInstall = installations.find(i => i.is_active);
            if (activeInstall) {
                this.historyVersionSelect.value = activeInstall.version;
                this.loadHistoricalLogs(activeInstall.version);
            }
        } catch (error) {
            console.error('Failed to load versions:', error);
            this.historyList.innerHTML = '<div class="loading-state">Error loading versions</div>';
        }
    }
    
    async loadHistoricalLogs(version) {
        this.historyList.innerHTML = '<div class="loading-state">Loading log files...</div>';
        
        try {
            const response = await fetch(`/api/logbackups/${version}`);
            const data = await response.json();
            const files = data.files || [];
            
            this.currentHistoryFiles = files; // Store for sorting
            this.historyCount.textContent = `${files.length} log${files.length !== 1 ? 's' : ''} found`;
            
            if (files.length === 0) {
                this.historyList.innerHTML = `
                    <div class="empty-history">
                        <div class="empty-history-icon">📜</div>
                        <div class="empty-history-text">No historical logs found</div>
                        <div class="empty-history-hint">Log backups will appear here after playing</div>
                    </div>
                `;
                return;
            }
            
            // Sort and render
            this.sortAndRenderHistory();
        } catch (error) {
            console.error('Failed to load log backups:', error);
            this.historyList.innerHTML = '<div class="loading-state">Error loading log files</div>';
        }
    }
    
    sortAndRenderHistory() {
        if (this.currentHistoryFiles.length === 0) return;
        
        const sortBy = this.historySortSelect.value;
        const files = [...this.currentHistoryFiles]; // Copy array
        
        // Sort based on selected option
        files.sort((a, b) => {
            switch (sortBy) {
                case 'date-desc':
                    return (b.date || '').localeCompare(a.date || '');
                case 'date-asc':
                    return (a.date || '').localeCompare(b.date || '');
                case 'size-desc':
                    return (b.size_bytes || 0) - (a.size_bytes || 0);
                case 'size-asc':
                    return (a.size_bytes || 0) - (b.size_bytes || 0);
                case 'name-asc':
                    return (a.filename || '').localeCompare(b.filename || '');
                case 'name-desc':
                    return (b.filename || '').localeCompare(a.filename || '');
                default:
                    return 0;
            }
        });
        
        // Render sorted files
        this.historyList.innerHTML = '';
        files.forEach(file => {
            const item = this.renderHistoryItem(file);
            this.historyList.appendChild(item);
        });
    }
    
    renderHistoryItem(file) {
        const item = document.createElement('div');
        item.className = 'history-item';
        
        // Format file size
        const sizeKB = Math.round(file.size_bytes / 1024);
        const sizeMB = (file.size_bytes / (1024 * 1024)).toFixed(2);
        const sizeStr = sizeKB > 1024 ? `${sizeMB} MB` : `${sizeKB} KB`;
        
        // Estimate line count (rough estimate: ~100 bytes per line)
        const estimatedLines = Math.round(file.size_bytes / 100).toLocaleString();
        
        item.innerHTML = `
            <div class="history-item-left">
                <div class="history-item-header">
                    <span class="history-item-title">${file.filename}</span>
                </div>
                <div class="history-item-info">
                    <span><strong>Size:</strong> ${sizeStr}</span>
                    <span><strong>~Lines:</strong> ${estimatedLines}</span>
                    ${file.build ? `<span><strong>Build:</strong> ${file.build}</span>` : ''}
                </div>
            </div>
            <div class="history-item-right">
                <span class="history-item-date">${file.date || 'Unknown date'}</span>
                <div class="history-item-actions">
                    <button class="btn-view" data-file="${encodeURIComponent(file.path)}" data-filename="${file.filename}">
                        📊 View
                    </button>
                    <button class="btn-export" data-file="${encodeURIComponent(file.path)}" data-filename="${file.filename}">
                        💾 Export
                    </button>
                </div>
            </div>
        `;
        
        // Add event listeners
        const viewBtn = item.querySelector('.btn-view');
        const exportBtn = item.querySelector('.btn-export');
        
        viewBtn.addEventListener('click', () => {
            this.analyzeLog(file.path, file.filename);
        });
        
        exportBtn.addEventListener('click', () => {
            this.exportLogHTML(file.path, file.filename);
        });
        
        return item;
    }
    
    async analyzeLog(logPath, filename) {
        this.analysisModal.classList.add('show');
        this.analysisTitle.textContent = `Analysis: ${filename}`;
        this.analysisContent.innerHTML = '<div class="loading-state">Analyzing log file...</div>';
        this.currentAnalyzedLog = { path: logPath, filename: filename };
        
        try {
            const response = await fetch('/api/analyze_log', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ log_file: logPath })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.renderAnalysisResults(data);
            } else {
                throw new Error(data.message || 'Analysis failed');
            }
        } catch (error) {
            console.error('Failed to analyze log:', error);
            this.analysisContent.innerHTML = `
                <div class="loading-state">
                    Error: ${error.message}
                </div>
            `;
        }
    }
    
    renderAnalysisResults(data) {
        const stats = data.stats || {};
        const events = data.events || [];
        const system_info = data.system_info || {};
        
        // Calculate uptime if we have timestamps
        let uptimeInfo = '';
        if (events && events.length >= 2) {
            const firstTime = new Date(events[0].timestamp);
            const lastTime = new Date(events[events.length - 1].timestamp);
            const uptimeMs = lastTime - firstTime;
            const uptimeHours = Math.floor(uptimeMs / (1000 * 60 * 60));
            const uptimeMinutes = Math.floor((uptimeMs % (1000 * 60 * 60)) / (1000 * 60));
            uptimeInfo = `${uptimeHours}h ${uptimeMinutes}m`;
        }
        
        // Compact two-column layout
        let html = `
            <div class="analysis-compact">
                <div class="analysis-row">
                    <div class="analysis-col">
                        <h3>📊 Events</h3>
                        <div class="compact-stats">
                            <div class="compact-stat"><span class="stat-label">Ship PvE:</span> <span class="stat-value pve">${stats.pve_kills || 0}</span></div>
                            <div class="compact-stat"><span class="stat-label">Ship PvP:</span> <span class="stat-value pvp">${stats.pvp_kills || 0}</span></div>
                            <div class="compact-stat"><span class="stat-label">Deaths:</span> <span class="stat-value death">${stats.deaths || 0}</span></div>
                            <div class="compact-stat"><span class="stat-label">FPS PvE:</span> <span class="stat-value fps-pve">${stats.fps_pve_kills || 0}</span></div>
                            <div class="compact-stat"><span class="stat-label">FPS PvP:</span> <span class="stat-value fps-pvp">${stats.fps_pvp_kills || 0}</span></div>
                            <div class="compact-stat"><span class="stat-label">FPS Death:</span> <span class="stat-value fps-death">${stats.fps_deaths || 0}</span></div>
                            <div class="compact-stat"><span class="stat-label">Soft Deaths:</span> <span class="stat-value vehicle-soft">${stats.vehicle_destroy_soft || 0}</span></div>
                            <div class="compact-stat"><span class="stat-label">Destructions:</span> <span class="stat-value vehicle-full">${stats.vehicle_destroy_full || 0}</span></div>
                            <div class="compact-stat"><span class="stat-label">Disconnects:</span> <span class="stat-value disconnect">${stats.disconnects || 0}</span></div>
                            <div class="compact-stat"><span class="stat-label">Stalls:</span> <span class="stat-value stall">${stats.actor_stalls || 0}</span></div>
                            <div class="compact-stat"><span class="stat-label">Suicides:</span> <span class="stat-value suicide">${stats.suicides || 0}</span></div>
                            <div class="compact-stat"><span class="stat-label">Corpses:</span> <span class="stat-value corpse">${stats.corpses || 0}</span></div>
                        </div>
                    </div>
                    <div class="analysis-col">
                        <h3>⏱️ Session Info</h3>
                        <div class="compact-stats">
                            <div class="compact-stat"><span class="stat-label">Total Lines:</span> <span class="stat-value">${stats.total_lines || 0}</span></div>
                            ${uptimeInfo ? `<div class="compact-stat"><span class="stat-label">Session Time:</span> <span class="stat-value">${uptimeInfo}</span></div>` : ''}
                            ${system_info.branch ? `<div class="compact-stat"><span class="stat-label">Branch:</span> <span class="stat-value">${system_info.branch}</span></div>` : ''}
                            ${system_info.changelist ? `<div class="compact-stat"><span class="stat-label">Build:</span> <span class="stat-value">${system_info.changelist}</span></div>` : ''}
                        </div>
                    </div>
                </div>
        `;
        
        // System info section (always show if available)
        if (system_info && (system_info.cpu || system_info.gpu || system_info.os)) {
            html += `
                <div class="analysis-system">
                    <h3>💻 System Info</h3>
                    <div class="system-grid">
                        ${system_info.os ? `<div class="system-item"><strong>OS:</strong> ${system_info.os}</div>` : ''}
                        ${system_info.cpu ? `<div class="system-item"><strong>CPU:</strong> ${system_info.cpu} ${system_info.cpu_cores ? `(${system_info.cpu_cores} cores)` : ''}</div>` : ''}
                        ${system_info.ram_total ? `<div class="system-item"><strong>RAM:</strong> ${Math.round(system_info.ram_total/1024)}GB</div>` : ''}
                        ${system_info.gpu ? `<div class="system-item"><strong>GPU:</strong> ${system_info.gpu}</div>` : ''}
                        ${system_info.gpu_vram ? `<div class="system-item"><strong>VRAM:</strong> ${Math.round(system_info.gpu_vram/1024)}GB</div>` : ''}
                        ${system_info.display_mode ? `<div class="system-item"><strong>Display:</strong> ${system_info.display_mode}</div>` : ''}
                        ${system_info.performance_cpu && system_info.performance_gpu ? `<div class="system-item"><strong>Performance Index:</strong> ${system_info.performance_cpu} (CPU), ${system_info.performance_gpu} (GPU)</div>` : ''}
                    </div>
                </div>
            `;
        }
        
        // Event timeline (only if events exist)
        if (events.length > 0) {
            const displayEvents = events.slice(-50);
            html += `
                <div class="analysis-timeline-section">
                    <h3>📜 Event Timeline (Last ${displayEvents.length}${events.length > 50 ? ` of ${events.length}` : ''})</h3>
                    <div class="analysis-timeline">
            `;
            
            displayEvents.forEach(event => {
                const eventClass = event.type.toLowerCase().replaceAll('_', '');
                html += `
                    <div class="timeline-event ${eventClass}">
                        <span class="timeline-timestamp">${event.timestamp || 'N/A'}</span>
                        <span class="timeline-details">${this.formatEventDetails(event)}</span>
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
        }
        
        html += `</div>`;
        
        this.analysisContent.innerHTML = html;
    }
    
    formatEventDetails(event) {
        switch (event.type) {
            case 'pve_kill':
                return `Ship PvE Kill: ${event.details?.target || 'Unknown target'}`;
            case 'pvp_kill':
                return `Ship PvP Kill: ${event.details?.target || 'Unknown player'}`;
            case 'fps_pve_kill':
                return `FPS PvE Kill: ${event.details?.target || 'Unknown target'}`;
            case 'fps_pvp_kill':
                return `FPS PvP Kill: ${event.details?.target || 'Unknown player'}`;
            case 'death':
                return `Death: ${event.details?.reason || 'Unknown cause'}`;
            case 'fps_death':
                return `FPS Death: ${event.details?.reason || 'Unknown cause'}`;
            case 'disconnect':
                return 'Disconnected from server';
            case 'actor_stall':
                if (event.details?.player && event.details?.stall_type && event.details?.length) {
                    return `Actor Stall: ${event.details.player} (${event.details.stall_type}, ${event.details.length}s)`;
                }
                return 'Actor Stall (Crash/Freeze)';
            case 'suicide':
                const suicidePlayer = event.details?.victim || 'Unknown';
                const suicideDamage = event.details?.damage_type || 'Unknown';
                return `Suicide 💀: ${suicidePlayer} (${suicideDamage})`;
            case 'corpse':
                if (event.details?.player && event.details?.status) {
                    return `Corpse 💀: ${event.details.player} - ${event.details.status}`;
                }
                return 'Player Corpse 💀';
            case 'vehicle_destroy_soft':
                const softShip = event.details?.ship_name || 'Unknown';
                const softAttacker = event.details?.attacker || 'Unknown';
                const softDamage = event.details?.damage_type || '';
                const softCrew = event.details?.crew_count || 0;
                let softText = `${softShip} disabled by ${softAttacker}`;
                if (softDamage) softText += ` (${softDamage})`;
                if (softCrew > 0) softText += ` +${softCrew} crew`;
                return softText;
            case 'vehicle_destroy_full':
                const fullShip = event.details?.ship_name || 'Unknown';
                const fullAttacker = event.details?.attacker || 'Unknown';
                const fullDamage = event.details?.damage_type || '';
                const fullCrew = event.details?.crew_count || 0;
                let fullText = `${fullShip} destroyed by ${fullAttacker}`;
                if (fullDamage) fullText += ` (${fullDamage})`;
                if (fullCrew > 0) fullText += ` +${fullCrew} crew`;
                return fullText;
            default:
                return event.type;
        }
    }
    
    async exportCurrentLog() {
        if (!this.currentAnalyzedLog) return;
        
        this.exportHtmlBtn.disabled = true;
        this.exportHtmlBtn.textContent = 'Exporting...';
        
        try {
            await this.exportLogHTML(this.currentAnalyzedLog.path, this.currentAnalyzedLog.filename);
        } finally {
            this.exportHtmlBtn.disabled = false;
            this.exportHtmlBtn.textContent = 'Export HTML Report';
        }
    }
    
    async exportLogHTML(logPath, filename) {
        try {
            console.log('Exporting log:', logPath);
            
            const response = await fetch('/api/export_log', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ log_file: logPath, format: 'full' })
            });
            
            if (!response.ok) {
                // Try to get error message from response
                const errorData = await response.json().catch(() => ({ message: 'Export failed' }));
                throw new Error(errorData.message || `Export failed with status ${response.status}`);
            }
            
            // Check content type
            const contentType = response.headers.get('content-type');
            console.log('Response content type:', contentType);
            
            // Get the HTML blob
            const blob = await response.blob();
            console.log('Blob size:', blob.size, 'bytes');
            
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // Clean filename for download
            const cleanFilename = filename.replace(/[^a-zA-Z0-9_\-\.]/g, '_');
            a.download = `starlogs_${cleanFilename}.html`;
            
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            this.showMessage('HTML report exported successfully', 'success');
        } catch (error) {
            console.error('Failed to export:', error);
            this.showMessage(`Failed to export: ${error.message}`, 'error');
        }
    }
    
    async loadBadgeVisibility() {
        // Load badge visibility preferences from server and apply to UI
        try {
            console.log('[DEBUG] Starting loadBadgeVisibility...');
            const response = await fetch('/api/badge_visibility');
            const data = await response.json();
            
            console.log('[DEBUG] Loaded badge visibility from server:', data);
            
            // Update filters with loaded preferences
            Object.keys(data).forEach(key => {
                if (key in this.filters) {
                    this.filters[key] = data[key];
                    console.log(`[DEBUG] Set filter ${key} to ${data[key]}`);
                }
            });
            
            // Update UI to reflect loaded preferences
            document.querySelectorAll('.count-badge[data-filter]').forEach(badge => {
                const filterName = badge.dataset.filter;
                const isActive = this.filters[filterName];
                
                console.log(`[DEBUG] Badge ${filterName}: isActive=${isActive}`);
                
                if (isActive) {
                    badge.classList.add('active');
                } else {
                    badge.classList.remove('active');
                }
            });
            
            // Apply filtering to existing events
            this.filterEvents();
            
            console.log('[DEBUG] Badge visibility fully loaded and applied');
        } catch (e) {
            console.error('Error loading badge visibility:', e);
            // Use defaults if error
            console.log('[DEBUG] Using default filter state (all active)');
        }
    }
    
    async saveBadgeVisibility() {
        // Save current badge visibility preferences to server.
        try {
            const response = await fetch('/api/badge_visibility', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(this.filters)
            });
            
            const result = await response.json();
            if (result.status === 'success') {
                console.log('[DEBUG] Badge visibility saved');
            } else {
                console.warn('Failed to save badge visibility:', result);
            }
        } catch (e) {
            console.error('Error saving badge visibility:', e);
        }
    }
    
    openAboutModal() {
        // Open the about modal and load content
        if (this.settingsMenu) {
            this.settingsMenu.classList.add('show');
            this.loadAboutInfo(); // Load about info when opening via ? button
            // Switch to about tab if it exists
            const tabBtn = document.querySelector('[data-tab="about"]');
            if (tabBtn) {
                tabBtn.click();
            }
        }
    }
}

// Toggle section collapse
function toggleSection(sectionId) {
    const content = document.getElementById(`${sectionId}-content`);
    const toggle = document.getElementById(`${sectionId}-toggle`);
    
    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        toggle.classList.remove('collapsed');
        toggle.textContent = '▼';
    } else {
        content.classList.add('collapsed');
        toggle.classList.add('collapsed');
        toggle.textContent = '▶';
    }
}

// Toggle badges visibility
function toggleBadges(event) {
    event.stopPropagation();
    const badgesContent = document.getElementById('badges-content');
    const badgesIcon = document.querySelector('.badges-toggle-icon');
    
    if (badgesContent.classList.contains('collapsed')) {
        badgesContent.classList.remove('collapsed');
        badgesIcon.classList.remove('collapsed');
        badgesIcon.textContent = '▼';
        localStorage.setItem('starlogger-badges-visible', 'true');
    } else {
        badgesContent.classList.add('collapsed');
        badgesIcon.classList.add('collapsed');
        badgesIcon.textContent = '▶';
        localStorage.setItem('starlogger-badges-visible', 'false');
    }
}

// Global functions for modal close buttons
function closeSettings() {
    document.getElementById('settings-menu').classList.remove('show');
}

function closeAbout() {
    document.getElementById('about-modal').classList.remove('show');
}

function closeHistory() {
    document.getElementById('history-modal').classList.remove('show');
}

function closeAnalysis() {
    document.getElementById('analysis-modal').classList.remove('show');
}

// Initialize app
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new StarLogsApp();
});

