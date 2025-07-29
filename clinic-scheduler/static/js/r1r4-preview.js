// R1 & R4 Preview Modal Functions

function showR1R4Preview(previewData) {
    hideLoading();
    
    const { r1_schedule, r4_fixed_schedules } = previewData;
    
    // Create modal content
    let modalHtml = `
        <div class="modal fade" id="r1PreviewModal" tabindex="-1">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">R1 & R4 預排門診預覽</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h6>R1 門診安排</h6>
                                <p class="text-muted small">您可以拖曳 R1 人員到不同的時段進行調整</p>
                                
                                <div class="r1-schedule-grid">
                                    <table class="table table-bordered table-sm">
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
        for (const [personId, assignment] of Object.entries(r1_schedule.clinic_assignments)) {
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
                     data-person-name="${assignedPerson.info.name || ''}"
                     ondragstart="handleDragStart(event)">
                    ${assignedPerson.id}${assignedPerson.info.name ? ' - ' + assignedPerson.info.name : ''} (${assignedPerson.info.rotation_unit})
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
                                    <h6>未分配 R1 人員</h6>
                                    <div class="r1-slot unassigned-slot" data-day="unassigned" 
                                         ondrop="handleDrop(event)" ondragover="allowDrop(event)"
                                         style="min-height: 50px; background-color: #f8f9fa; border: 2px dashed #dee2e6; padding: 8px;">
                                        <!-- Unassigned personnel will appear here -->
                                    </div>
                                </div>
                                
                                <div class="mt-3">
                                    <h6>健康檢查排班</h6>
                                    <div class="text-muted small">
    `;
    
    // Show health check assignments
    for (const [personId, assignments] of Object.entries(r1_schedule.health_check_assignments)) {
        modalHtml += `<p><strong>${personId}:</strong> ${assignments.length} 個體檢時段</p>`;
    }
    
    modalHtml += `
                                    </div>
                                </div>
                            </div>
                            
                            <div class="col-md-6">
                                <h6>R4 指定門診時間</h6>
                                <p class="text-muted small">以下為 R4 人員指定的固定門診時間</p>
                                
                                <div class="r4-fixed-schedules">
                                    <table class="table table-bordered table-sm">
                                        <thead>
                                            <tr>
                                                <th>人員</th>
                                                <th>星期</th>
                                                <th>時段</th>
                                                <th>診間</th>
                                            </tr>
                                        </thead>
                                        <tbody>
    `;
    
    // Add R4 fixed schedules
    if (r4_fixed_schedules && Object.keys(r4_fixed_schedules).length > 0) {
        const dayNamesMap = {
            'Monday': '週一',
            'Tuesday': '週二',
            'Wednesday': '週三',
            'Thursday': '週四',
            'Friday': '週五'
        };
        const timeNames = {
            'Morning': '上午',
            'Afternoon': '下午'
        };
        
        for (const [personId, schedule] of Object.entries(r4_fixed_schedules)) {
            modalHtml += `
                <tr>
                    <td>${personId}${schedule.person_info.name ? ' - ' + schedule.person_info.name : ''} (${schedule.person_info.rotation_unit})</td>
                    <td>${dayNamesMap[schedule.day] || schedule.day}</td>
                    <td>${timeNames[schedule.time] || schedule.time}</td>
                    <td>${schedule.room ? `<span class="badge bg-success">${schedule.room}</span>` : '<span class="badge bg-secondary">待分配</span>'}
                </tr>
            `;
        }
    } else {
        modalHtml += `
            <tr>
                <td colspan="4" class="text-center text-muted">無 R4 指定門診時間</td>
            </tr>
        `;
    }
    
    modalHtml += `
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" onclick="confirmR1R4Schedule()">確認並繼續排班</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Handle unassigned R1 personnel
    handleUnassignedR1(r1_schedule);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('r1PreviewModal'));
    modal.show();
    
    // Clean up modal when hidden
    document.getElementById('r1PreviewModal').addEventListener('hidden.bs.modal', function () {
        this.remove();
    });
}

function handleUnassignedR1(r1Schedule) {
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
                personElement.dataset.personName = person.name || '';
                personElement.textContent = `${person.id}${person.name ? ' - ' + person.name : ''} (${person.rotation_unit})`;
                personElement.ondragstart = handleDragStart;
                unassignedSlot.appendChild(personElement);
            }
        }
        
        // If no unassigned personnel, show placeholder
        if (unassignedSlot.children.length === 0) {
            unassignedSlot.innerHTML = '<span class="text-muted">將人員拖曳至此處以暫時移出排班</span>';
        }
    }
}

// Modified confirm function to handle both R1 and R4
async function confirmR1R4Schedule() {
    try {
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('r1PreviewModal'));
        modal.hide();
        
        // Show loading
        showLoading('正在使用基因演算法生成完整排班表...');
        
        // Collect form data again
        const formData = collectFormData();
        
        // Add modified R1 schedule and R4 fixed schedules
        formData.r1_schedule = r1PreviewData.r1_schedule;
        formData.r4_fixed_schedules = r1PreviewData.r4_fixed_schedules;
        
        // Send request with modified schedules
        const response = await fetch('/api/schedule-with-r1', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Store result data
            currentTaskId = result.task_id;
            scheduleData = result;
            
            // Show success message
            document.getElementById('resultMessage').innerHTML = `
                <i class="fas fa-check-circle"></i> 排班生成成功！<br>
                覆蓋率: ${result.statistics.coverage_rate?.toFixed(1) || 0}% | 
                健檢覆蓋率: ${result.statistics.health_check_coverage?.toFixed(1) || 0}%
            `;
            
            // Display schedule and validation results
            if (typeof displaySchedule === 'function') {
                displaySchedule(result);
            }
            
            if (typeof displayRulesValidation === 'function' && result.violations) {
                displayRulesValidation(result.violations);
            }
            
            // Show results section
            document.getElementById('resultsSection').style.display = 'block';
            document.getElementById('errorSection').style.display = 'none';
            
            // Scroll to results
            document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
        } else {
            // Show error
            showError(result.error, result.details);
        }
        
    } catch (error) {
        showError('系統錯誤: ' + error.message);
    } finally {
        hideLoading();
    }
}