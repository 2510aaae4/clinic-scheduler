// Global variables for R1 preview
let r1PreviewData = null;
let draggedPerson = null;

// Personnel configuration
const personnelConfig = {
    R1: { default: 5, min: 1, max: 10, current: 5 },
    R2: { default: 6, min: 1, max: 10, current: 6 },
    R3: { default: 4, min: 1, max: 10, current: 4 },
    R4: { default: 6, min: 1, max: 10, current: 6 }
};

// Rotation units by level
const rotationUnits = {
    R1: ['內科病房', '健康', '急診', '兒科病房', '精神1', '社區1', '婦產病房', '放射'],
    R2: ['婦產門診', '內科病房', '兒科門診', '外科病房', '社區2', '眼科門診', '皮膚門診', 
         '神內門診', '復健門診', 'ENT門診', '精神2', '家庭醫業'],
    R3: ['CR', '斗六1', '神內門診', '泌尿門診', '糖尿病衛教', '安寧1', '老醫門診', 
         '安寧2', '內科門診', '放射'],
    R4: ['睡眠門診', '旅遊門診', '骨鬆門診', '減重門診', '疼痛科', '斗六2', '其他']
};

// Personnel labels
const personnelLabels = {};

// Initialize forms on page load
function initializeForms() {
    // Generate forms for each level
    for (const level of ['R1', 'R2', 'R3', 'R4']) {
        updatePersonnelForms(level, 0, personnelConfig[level].default);
    }
}

// Adjust personnel count
function adjustCount(level, delta) {
    const config = personnelConfig[level];
    const newCount = Math.max(config.min, Math.min(config.max, config.current + delta));
    
    if (newCount !== config.current) {
        const oldCount = config.current;
        config.current = newCount;
        
        // Update display
        document.getElementById(`${level.toLowerCase()}-count`).value = newCount;
        
        // Update forms
        updatePersonnelForms(level, oldCount, newCount);
    }
}

// Update personnel forms based on count
function updatePersonnelForms(level, oldCount, newCount) {
    const container = document.getElementById(`${level.toLowerCase()}-personnel`);
    
    if (newCount > oldCount) {
        // Add new forms
        for (let i = oldCount; i < newCount; i++) {
            const label = getPersonnelLabel(level, i);
            const formHtml = createPersonnelForm(level, label, i);
            container.insertAdjacentHTML('beforeend', formHtml);
        }
    } else if (newCount < oldCount) {
        // Remove forms from the end
        const forms = container.querySelectorAll('.personnel-form');
        for (let i = oldCount - 1; i >= newCount; i--) {
            if (forms[i]) {
                forms[i].remove();
            }
        }
    }
}

// Get personnel label (A, B, C, etc.)
function getPersonnelLabel(level, index) {
    const letters = 'ABCDEFGHIJ';
    return `${level}_${letters[index]}`;
}

// Create personnel form HTML
function createPersonnelForm(level, label, index) {
    const units = rotationUnits[level];
    const isR4 = level === 'R4';
    
    let html = `
        <div class="col-md-6 mb-3 personnel-form">
            <div class="card">
                <div class="card-body">
                    <h6 class="card-title">${label}</h6>
                    <div class="mb-2">
                        <label class="form-label">姓名</label>
                        <input type="text" class="form-control" name="${label}_name" id="${label}_name" placeholder="請輸入姓名">
                    </div>
                    <div class="mb-2">
                        <label class="form-label">輪訓單位</label>
                        <select class="form-select" name="${label}_unit" id="${label}_unit" required>
                            <option value="">請選擇...</option>`;
    
    for (const unit of units) {
        html += `<option value="${unit}">${unit}</option>`;
    }
    
    html += `
                        </select>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" 
                               name="${label}_health" id="${label}_health">
                        <label class="form-check-label" for="${label}_health">
                            支援體檢
                        </label>
                    </div>`;
    
    if (isR4) {
        html += `
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" 
                               name="${label}_teaching" id="${label}_teaching">
                        <label class="form-check-label" for="${label}_teaching">
                            週二教學（不排門診）
                        </label>
                    </div>
                    <div class="mt-2">
                        <label class="form-label">指定門診時間（選填）</label>
                        <div class="row">
                            <div class="col-4">
                                <select class="form-select form-select-sm" name="${label}_fixed_day" id="${label}_fixed_day" onchange="updateRoomOptions('${label}')">
                                    <option value="">無</option>
                                    <option value="Monday">週一</option>
                                    <option value="Tuesday">週二</option>
                                    <option value="Wednesday">週三</option>
                                    <option value="Thursday">週四</option>
                                    <option value="Friday">週五</option>
                                </select>
                            </div>
                            <div class="col-4">
                                <select class="form-select form-select-sm" name="${label}_fixed_time" id="${label}_fixed_time" onchange="updateRoomOptions('${label}')">
                                    <option value="">無</option>
                                    <option value="Morning">上午</option>
                                    <option value="Afternoon">下午</option>
                                </select>
                            </div>
                            <div class="col-4">
                                <select class="form-select form-select-sm" name="${label}_fixed_room" id="${label}_fixed_room" disabled>
                                    <option value="">請先選擇日期與時段</option>
                                </select>
                            </div>
                        </div>
                    </div>`;
    }
    
    html += `
                </div>
            </div>
        </div>`;
    
    return html;
}

// Reset form
function resetForm() {
    if (confirm('確定要重設所有設定嗎？')) {
        // Reset counts
        for (const level of ['R1', 'R2', 'R3', 'R4']) {
            personnelConfig[level].current = personnelConfig[level].default;
            document.getElementById(`${level.toLowerCase()}-count`).value = personnelConfig[level].default;
        }
        
        // Reinitialize forms
        initializeForms();
        
        // Hide results
        document.getElementById('resultsSection').style.display = 'none';
        document.getElementById('errorSection').style.display = 'none';
    }
}

// Collect form data
function collectFormData() {
    const data = {
        personnel_counts: {
            R1: personnelConfig.R1.current,
            R2: personnelConfig.R2.current,
            R3: personnelConfig.R3.current,
            R4: personnelConfig.R4.current
        },
        personnel: {
            R1: {},
            R2: {},
            R3: {},
            R4: {}
        }
    };
    
    // Collect data for each level
    for (const level of ['R1', 'R2', 'R3', 'R4']) {
        const count = personnelConfig[level].current;
        
        for (let i = 0; i < count; i++) {
            const label = getPersonnelLabel(level, i);
            const name = document.getElementById(`${label}_name`)?.value || '';
            const unit = document.getElementById(`${label}_unit`)?.value;
            const healthCheck = document.getElementById(`${label}_health`)?.checked || false;
            
            if (!unit) {
                throw new Error(`請為 ${label} 選擇輪訓單位`);
            }
            
            data.personnel[level][label] = {
                name: name,
                rotation_unit: unit,
                health_check: healthCheck
            };
            
            // Add teaching flag and fixed time for R4
            if (level === 'R4') {
                data.personnel[level][label].tuesday_teaching = 
                    document.getElementById(`${label}_teaching`)?.checked || false;
                
                // Add fixed time slot if specified
                const fixedDay = document.getElementById(`${label}_fixed_day`)?.value;
                const fixedTime = document.getElementById(`${label}_fixed_time`)?.value;
                const fixedRoom = document.getElementById(`${label}_fixed_room`)?.value;
                if (fixedDay && fixedTime && fixedRoom) {
                    data.personnel[level][label].fixed_schedule = {
                        day: fixedDay,
                        time_slot: fixedTime,
                        room: fixedRoom
                    };
                }
            }
        }
    }
    
    return data;
}

// Generate schedule with R1 preview
async function generateSchedule() {
    try {
        // Collect form data
        const formData = collectFormData();
        
        // First, get R1 preview
        showLoading('正在生成 R1 預覽排班...');
        
        const previewResponse = await fetch('/api/preview-r1', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        // Check if response is ok
        if (!previewResponse.ok) {
            let errorMessage = `HTTP Error ${previewResponse.status}`;
            try {
                const errorData = await previewResponse.json();
                errorMessage = errorData.error || errorMessage;
            } catch (parseError) {
                console.error('Failed to parse error response:', parseError);
            }
            showError('無法生成 R1 預覽: ' + errorMessage);
            hideLoading();
            return;
        }
        
        // Check if response is JSON
        const contentType = previewResponse.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            showError('伺服器回傳非 JSON 格式');
            hideLoading();
            return;
        }
        
        let previewResult;
        try {
            previewResult = await previewResponse.json();
        } catch (parseError) {
            console.error('JSON parse error:', parseError);
            showError('無法解析伺服器回應');
            hideLoading();
            return;
        }
        
        if (!previewResult.success) {
            showError('無法生成 R1 預覽: ' + previewResult.error);
            hideLoading();
            return;
        }
        
        // Store R1 preview data
        r1PreviewData = previewResult;
        
        // Show R1 & R4 preview modal
        showR1R4Preview(previewResult);
        
    } catch (error) {
        showError('系統錯誤: ' + error.message);
        hideLoading();
    }
}

// Show R1 preview modal
function showR1Preview(r1Schedule) {
    hideLoading();
    
    // Create modal content
    let modalHtml = `
        <div class="modal fade" id="r1PreviewModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">R1 排班預覽</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p class="text-muted">您可以拖曳 R1 人員到不同的時段進行調整</p>
                        
                        <div class="r1-schedule-grid">
                            <table class="table table-bordered">
                                <thead>
                                    <tr>
                                        <th>星期</th>
                                        <th>下午 4204 診</th>
                                    </tr>
                                </thead>
                                <tbody>
    `;
    
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
    const dayNames = ['週一', '週二', '週三', '週四', '週五'];
    
    for (let i = 0; i < days.length; i++) {
        const day = days[i];
        const dayName = dayNames[i];
        
        // Find who is assigned to this day
        let assignedPerson = null;
        for (const [personId, assignment] of Object.entries(r1Schedule.clinic_assignments)) {
            if (assignment.day === day) {
                assignedPerson = {
                    id: personId,
                    info: assignment.person_info
                };
                break;
            }
        }
        
        modalHtml += `
            <tr>
                <td>${dayName}</td>
                <td class="r1-slot" data-day="${day}" ondrop="handleDrop(event)" ondragover="allowDrop(event)">
        `;
        
        if (assignedPerson) {
            modalHtml += `
                <div class="r1-person badge bg-info" draggable="true" 
                     data-person-id="${assignedPerson.id}"
                     ondragstart="handleDragStart(event)">
                    ${assignedPerson.id} (${assignedPerson.info.rotation_unit})
                </div>
            `;
        }
        
        modalHtml += `
                </td>
            </tr>
        `;
    }
    
    modalHtml += `
                                </tbody>
                            </table>
                        </div>
                        
                        <div class="mt-3">
                            <h6>健康檢查排班</h6>
                            <div class="text-muted small">
    `;
    
    // Show health check assignments
    for (const [personId, assignments] of Object.entries(r1Schedule.health_check_assignments)) {
        modalHtml += `<p><strong>${personId}:</strong> ${assignments.length} 個體檢時段</p>`;
    }
    
    modalHtml += `
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" onclick="confirmR1Schedule()">確認並繼續排班</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Add any unassigned R1 personnel to the unassigned slot
    const unassignedSlot = document.querySelector('.unassigned-slot');
    if (unassignedSlot && r1PreviewData && r1PreviewData.r1_personnel) {
        // First clear the placeholder text
        unassignedSlot.innerHTML = '';
        
        for (const person of r1PreviewData.r1_personnel) {
            const isAssigned = Object.keys(r1Schedule.clinic_assignments).includes(person.id);
            if (!isAssigned) {
                const personElement = document.createElement('div');
                personElement.className = 'r1-person badge bg-warning';
                personElement.draggable = true;
                personElement.dataset.personId = person.id;
                personElement.textContent = `${person.id} (${person.rotation_unit})`;
                personElement.ondragstart = handleDragStart;
                unassignedSlot.appendChild(personElement);
            }
        }
        
        // If no unassigned personnel, show placeholder
        if (unassignedSlot.children.length === 0) {
            unassignedSlot.innerHTML = '<span class="text-muted">將人員拖曳至此處以暫時移出排班</span>';
        }
    }
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('r1PreviewModal'));
    modal.show();
    
    // Clean up modal when hidden
    document.getElementById('r1PreviewModal').addEventListener('hidden.bs.modal', function () {
        this.remove();
    });
}

// Drag and drop functions
function allowDrop(event) {
    event.preventDefault();
}

function handleDragStart(event) {
    draggedPerson = {
        id: event.target.dataset.personId,
        element: event.target
    };
    event.dataTransfer.effectAllowed = 'move';
}

function handleDrop(event) {
    event.preventDefault();
    
    if (!draggedPerson) return;
    
    const targetSlot = event.target.closest('.r1-slot');
    if (!targetSlot) return;
    
    const targetDay = targetSlot.dataset.day;
    
    // Find the source slot (where the dragged person came from)
    const sourceSlot = draggedPerson.element.parentElement;
    const sourceDay = sourceSlot ? sourceSlot.dataset.day : null;
    
    // Check if there's an existing person in the target slot
    const existingPerson = targetSlot.querySelector('.r1-person');
    
    if (existingPerson && sourceSlot) {
        // Swap: Move existing person to source slot
        sourceSlot.appendChild(existingPerson);
        
        // Update the swapped person's data
        const existingPersonId = existingPerson.dataset.personId;
        if (sourceDay === 'unassigned') {
            // Moving to unassigned slot
            if (r1PreviewData && r1PreviewData.r1_schedule.clinic_assignments[existingPersonId]) {
                delete r1PreviewData.r1_schedule.clinic_assignments[existingPersonId];
            }
        } else if (r1PreviewData && r1PreviewData.r1_schedule.clinic_assignments[existingPersonId]) {
            r1PreviewData.r1_schedule.clinic_assignments[existingPersonId].day = sourceDay;
        }
    }
    
    // Clear placeholder text if dropping into unassigned slot
    if (targetDay === 'unassigned') {
        const placeholder = targetSlot.querySelector('.text-muted');
        if (placeholder) {
            placeholder.remove();
        }
    }
    
    // Add placeholder if source slot becomes empty
    if (sourceSlot && sourceSlot.classList.contains('unassigned-slot') && sourceSlot.children.length === 0) {
        sourceSlot.innerHTML = '<span class="text-muted">將人員拖曳至此處以暫時移出排班</span>';
    }
    
    // Move dragged person to target slot
    targetSlot.appendChild(draggedPerson.element);
    
    // Update dragged person's data
    if (r1PreviewData && r1PreviewData.r1_schedule.clinic_assignments[draggedPerson.id]) {
        r1PreviewData.r1_schedule.clinic_assignments[draggedPerson.id].day = targetDay;
    }
    
    draggedPerson = null;
}

// This function is now replaced by confirmR1R4Schedule in r1r4-preview.js
// Keep for backward compatibility
function confirmR1Schedule() {
    if (typeof confirmR1R4Schedule === 'function') {
        confirmR1R4Schedule();
    } else {
        console.error('confirmR1R4Schedule not found');
    }
}

// Show error message
function showError(message, details = null) {
    let errorHtml = `<p>${message}</p>`;
    
    if (details) {
        errorHtml += '<ul class="mb-0">';
        for (const [key, value] of Object.entries(details)) {
            errorHtml += `<li>${key}: ${value}</li>`;
        }
        errorHtml += '</ul>';
    }
    
    document.getElementById('errorMessage').innerHTML = errorHtml;
    document.getElementById('errorSection').style.display = 'block';
    document.getElementById('resultsSection').style.display = 'none';
    
    // Scroll to error
    document.getElementById('errorSection').scrollIntoView({ behavior: 'smooth' });
}

// Download CSV file
function downloadCSV(format) {
    if (!scheduleData || !scheduleData.files) {
        alert('請先生成排班表');
        return;
    }
    
    const filename = scheduleData.files[format];
    if (filename) {
        window.location.href = `/api/download/${format}/${filename}`;
    }
}

// Download all files as ZIP
async function downloadAll() {
    if (!currentTaskId) {
        alert('請先生成排班表');
        return;
    }
    
    window.location.href = `/api/download/zip/${currentTaskId}`;
}

// Show validation toast
function showValidation(message, type = 'warning') {
    const toast = document.getElementById('validationToast');
    const toastBody = document.getElementById('validationMessage');
    
    // Set message
    toastBody.textContent = message;
    
    // Set color based on type
    toast.classList.remove('bg-warning', 'bg-danger', 'bg-success');
    if (type === 'error') {
        toast.classList.add('bg-danger');
    } else if (type === 'success') {
        toast.classList.add('bg-success');
    } else {
        toast.classList.add('bg-warning');
    }
    
    // Show toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

// Available rooms by day and time slot
const AVAILABLE_ROOMS = {
    'Monday': {
        'Morning': ['4201', '4203', '4209', '4218'],
        'Afternoon': ['4201', '4202', '4203', '4207', '4208']
    },
    'Tuesday': {
        'Morning': ['4201', '4207', '4209'],
        'Afternoon': ['4201', '4205', '4208']
    },
    'Wednesday': {
        'Morning': ['4201', '4208', '4213', '4218'],
        'Afternoon': ['4201', '4203', '4207', '4208', '4209', '4213']
    },
    'Thursday': {
        'Morning': ['4201', '4213', '4218'],
        'Afternoon': ['4201', '4202', '4205', '4207', '4208']
    },
    'Friday': {
        'Morning': ['4201', '4205', '4218'],
        'Afternoon': ['4201', '4202', '4205', '4207', '4208']
    }
};

// Update room options based on selected day and time
function updateRoomOptions(label) {
    const daySelect = document.getElementById(`${label}_fixed_day`);
    const timeSelect = document.getElementById(`${label}_fixed_time`);
    const roomSelect = document.getElementById(`${label}_fixed_room`);
    
    const day = daySelect.value;
    const time = timeSelect.value;
    
    // Clear room options
    roomSelect.innerHTML = '';
    
    if (day && time && AVAILABLE_ROOMS[day] && AVAILABLE_ROOMS[day][time]) {
        // Enable room select
        roomSelect.disabled = false;
        
        // Add default option
        roomSelect.innerHTML = '<option value="">選擇診間</option>';
        
        // Add available rooms for this time slot
        // Exclude 4204 (reserved for R1) and 4201 (R2/R3 preferred)
        const availableRooms = AVAILABLE_ROOMS[day][time].filter(room => room !== '4204');
        
        availableRooms.forEach(room => {
            const option = document.createElement('option');
            option.value = room;
            option.textContent = room;
            if (room === '4201') {
                option.textContent += ' (R2/R3優先)';
            }
            roomSelect.appendChild(option);
        });
    } else {
        // Disable room select
        roomSelect.disabled = true;
        roomSelect.innerHTML = '<option value="">請先選擇日期與時段</option>';
    }
}

// Show loading overlay
function showLoading(message = '處理中...') {
    const loadingHtml = `
        <div class="loading-overlay" id="loadingOverlay">
            <div class="spinner-container">
                <div class="spinner-border text-light" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-3">${message}</p>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', loadingHtml);
}

// Hide loading overlay
function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.remove();
    }
}

// Real-time validation
document.addEventListener('change', async function(event) {
    if (event.target.tagName === 'SELECT' && event.target.name.includes('_unit')) {
        // Validate rotation unit selection
        const parts = event.target.name.split('_');
        const level = parts[0];
        const value = event.target.value;
        
        if (value) {
            // Send validation request
            const response = await fetch('/api/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    level: level,
                    field: 'rotation_unit',
                    value: value
                })
            });
            
            const result = await response.json();
            
            if (!result.valid && result.errors.length > 0) {
                showValidation(result.errors[0], 'error');
            }
        }
    }
});