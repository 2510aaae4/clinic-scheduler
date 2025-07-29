// Schedule Display Functions

// Level colors
const LEVEL_COLORS = {
    'R1': '#17a2b8',  // info blue
    'R2': '#28a745',  // success green
    'R3': '#ffc107',  // warning yellow
    'R4': '#dc3545'   // danger red
};

// Display schedule with color coding
function displaySchedule(scheduleData) {
    const container = document.getElementById('schedulePreview');
    
    // Create schedule table
    let html = `
        <h5 class="mb-3">
            <i class="fas fa-calendar-alt"></i> 排班結果預覽
        </h5>
        <div class="table-responsive">
            <table class="table table-bordered table-sm schedule-display-table">
                <thead class="table-dark">
                    <tr>
                        <th rowspan="2" style="vertical-align: middle;">診間</th>
    `;
    
    // Add day headers
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
    const dayNames = ['週一', '週二', '週三', '週四', '週五'];
    
    for (let i = 0; i < days.length; i++) {
        html += `<th colspan="2" class="text-center">${dayNames[i]}</th>`;
    }
    
    html += `
                    </tr>
                    <tr>
    `;
    
    // Add time slot headers
    for (let i = 0; i < days.length; i++) {
        html += `<th class="text-center">上午</th><th class="text-center">下午</th>`;
    }
    
    html += `
                    </tr>
                </thead>
                <tbody>
    `;
    
    // Get all rooms from schedule
    const rooms = new Set();
    const schedule = scheduleData.schedule.W1;
    
    for (const day of days) {
        if (schedule[day]) {
            for (const timeSlot of ['Morning', 'Afternoon']) {
                if (schedule[day][timeSlot]) {
                    Object.keys(schedule[day][timeSlot]).forEach(room => rooms.add(room));
                }
            }
        }
    }
    
    // Sort rooms
    const sortedRooms = Array.from(rooms).sort((a, b) => {
        // Put health check rooms at the end
        if (a.includes('體檢') && !b.includes('體檢')) return 1;
        if (!a.includes('體檢') && b.includes('體檢')) return -1;
        return a.localeCompare(b);
    });
    
    // Create rows for each room
    for (const room of sortedRooms) {
        html += `<tr><td class="fw-bold">${room}</td>`;
        
        for (const day of days) {
            for (const timeSlot of ['Morning', 'Afternoon']) {
                const person = schedule[day]?.[timeSlot]?.[room] || '';
                
                if (person) {
                    const level = person.substring(0, 2); // Extract R1, R2, etc.
                    const color = LEVEL_COLORS[level] || '#6c757d';
                    const personInfo = getPersonInfo(person, scheduleData.statistics);
                    
                    html += `
                        <td class="text-center" style="background-color: ${color}20;">
                            <span class="badge" style="background-color: ${color};">
                                ${person}
                            </span>
                            ${personInfo.name ? `<br><small>${personInfo.name}</small>` : ''}
                        </td>
                    `;
                } else {
                    html += `<td class="text-center text-muted">-</td>`;
                }
            }
        }
        
        html += `</tr>`;
    }
    
    html += `
                </tbody>
            </table>
        </div>
        
        <div class="mt-3">
            <div class="row">
                <div class="col-md-6">
                    <h6>圖例說明：</h6>
                    <div class="d-flex flex-wrap gap-2">
                        <span class="badge" style="background-color: ${LEVEL_COLORS.R1};">R1</span>
                        <span class="badge" style="background-color: ${LEVEL_COLORS.R2};">R2</span>
                        <span class="badge" style="background-color: ${LEVEL_COLORS.R3};">R3</span>
                        <span class="badge" style="background-color: ${LEVEL_COLORS.R4};">R4</span>
                    </div>
                </div>
                <div class="col-md-6">
                    <h6>統計資訊：</h6>
                    <small>
                        覆蓋率: ${scheduleData.statistics.coverage_rate?.toFixed(1) || 0}% | 
                        健檢覆蓋率: ${scheduleData.statistics.health_check_coverage?.toFixed(1) || 0}%
                    </small>
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

// Display rules validation results
function displayRulesValidation(violations) {
    const container = document.getElementById('rulesValidation');
    
    // Define all rules to check
    const allRules = [
        {
            category: 'R1 規則',
            rules: [
                { name: '健康單位必須排滿8個體檢時段', key: 'r1_health_8_checks' },
                { name: '健康單位必須排週一下午4204診', key: 'r1_health_monday_4204' },
                { name: '社區1必須排週二下午4204診', key: 'r1_community_tuesday' },
                { name: '病房單位不能排週一、週五', key: 'r1_ward_restriction' },
                { name: '精神1不能排週一下午、週四下午', key: 'r1_mental_restriction' },
                { name: 'R1門診必須在下午4204診', key: 'r1_afternoon_4204' }
            ]
        },
        {
            category: 'R2 規則',
            rules: [
                { name: '每人必須排恰好一個4201診', key: 'r2_one_4201' },
                { name: '兩個門診必須分別在上午和下午', key: 'r2_different_times' },
                { name: '社區2必須排週三下午和週五上午', key: 'r2_community_schedule' },
                { name: '皮膚門診不能排週三', key: 'r2_skin_restriction' },
                { name: '復健門診不能排週三上午', key: 'r2_rehab_restriction' }
            ]
        },
        {
            category: 'R3 規則',
            rules: [
                { name: '每人必須排恰好一個4201診', key: 'r3_one_4201' },
                { name: '至少要有一個上午門診', key: 'r3_morning_required' },
                { name: '斗六1必須排週二上午4201診', key: 'r3_douliu_tuesday' },
                { name: 'CR必須排週一上午、週二下午、週四下午', key: 'r3_cr_schedule' },
                { name: '安寧1不能排週一上午', key: 'r3_hospice1_restriction' }
            ]
        },
        {
            category: 'R4 規則',
            rules: [
                { name: '至少要有一個上午門診', key: 'r4_morning_required' },
                { name: '週二教學者不能排任何門診', key: 'r4_tuesday_teaching' },
                { name: '旅遊門診不能排週一下午、週五下午', key: 'r4_travel_restriction' },
                { name: '旅遊門診最多2個門診', key: 'r4_travel_max_2' },
                { name: '指定門診時間必須被遵守', key: 'r4_fixed_schedule' }
            ]
        },
        {
            category: '一般規則',
            rules: [
                { name: '同一人不能同時出現在多個診間', key: 'no_double_booking' },
                { name: '所有必要診間都有人值班', key: 'all_rooms_filled' },
                { name: '同一人不能上下午都有班（除R1健康）', key: 'no_full_day' },
                { name: '4201診只能由R2或R3擔任', key: '4201_restriction' },
                { name: '4204診下午保留給R1', key: '4204_r1_only' }
            ]
        }
    ];
    
    // Check violations
    const violationMessages = [];
    if (violations) {
        if (violations.hard_violations) {
            violationMessages.push(...violations.hard_violations);
        }
        if (violations.soft_violations) {
            violationMessages.push(...violations.soft_violations);
        }
    }
    
    let html = `
        <h5 class="mb-3">
            <i class="fas fa-check-circle"></i> 規則檢查結果
        </h5>
        <div class="accordion" id="rulesAccordion">
    `;
    
    // Display each category
    allRules.forEach((category, index) => {
        const categoryViolations = category.rules.filter(rule => 
            violationMessages.some(msg => msg.toLowerCase().includes(rule.key) || 
                                        checkRuleViolation(rule, violationMessages))
        ).length;
        
        const allPassed = categoryViolations === 0;
        const accordionId = `category${index}`;
        
        html += `
            <div class="accordion-item">
                <h2 class="accordion-header">
                    <button class="accordion-button ${allPassed ? 'collapsed' : ''}" 
                            type="button" 
                            data-bs-toggle="collapse" 
                            data-bs-target="#${accordionId}">
                        <span class="${allPassed ? 'text-success' : 'text-danger'}">
                            ${category.category} 
                            ${allPassed ? 
                                '<i class="fas fa-check-circle ms-2"></i>' : 
                                `<i class="fas fa-times-circle ms-2"></i> (${categoryViolations} 項違規)`
                            }
                        </span>
                    </button>
                </h2>
                <div id="${accordionId}" 
                     class="accordion-collapse collapse ${allPassed ? '' : 'show'}"
                     data-bs-parent="#rulesAccordion">
                    <div class="accordion-body">
                        <ul class="list-unstyled mb-0">
        `;
        
        category.rules.forEach(rule => {
            const isViolated = checkRuleViolation(rule, violationMessages);
            html += `
                <li class="mb-2">
                    ${isViolated ? 
                        '<i class="fas fa-times text-danger"></i>' : 
                        '<i class="fas fa-check text-success"></i>'
                    }
                    <span class="${isViolated ? 'text-danger' : ''}">
                        ${rule.name}
                    </span>
                </li>
            `;
        });
        
        html += `
                        </ul>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += `
        </div>
        
        ${violationMessages.length > 0 ? `
            <div class="mt-3">
                <h6>違規詳情：</h6>
                <div class="alert alert-danger">
                    <ul class="mb-0">
                        ${violationMessages.map(msg => `<li>${msg}</li>`).join('')}
                    </ul>
                </div>
            </div>
        ` : `
            <div class="mt-3">
                <div class="alert alert-success">
                    <i class="fas fa-check-circle"></i> 所有規則檢查通過！
                </div>
            </div>
        `}
    `;
    
    container.innerHTML = html;
}

// Helper function to check if a rule is violated
function checkRuleViolation(rule, violationMessages) {
    // More comprehensive rule checking
    return violationMessages.some(msg => {
        const lowerMsg = msg.toLowerCase();
        
        switch(rule.key) {
            case 'r1_health_8_checks':
                return lowerMsg.includes('健康') && lowerMsg.includes('8') && lowerMsg.includes('health check');
            case 'r1_health_monday_4204':
                return lowerMsg.includes('健康') && lowerMsg.includes('monday') && lowerMsg.includes('4204');
            case 'r1_community_tuesday':
                return lowerMsg.includes('社區1') && lowerMsg.includes('tuesday');
            case 'r1_ward_restriction':
                return lowerMsg.includes('病房') && (lowerMsg.includes('monday') || lowerMsg.includes('friday'));
            case 'r1_mental_restriction':
                return lowerMsg.includes('精神1') && (lowerMsg.includes('monday') || lowerMsg.includes('thursday'));
            case 'r1_afternoon_4204':
                return lowerMsg.includes('r1') && lowerMsg.includes('4204') && lowerMsg.includes('afternoon');
            case 'r2_one_4201':
                return lowerMsg.includes('r2') && lowerMsg.includes('4201') && lowerMsg.includes('exactly one');
            case 'r2_different_times':
                return lowerMsg.includes('r2') && lowerMsg.includes('different times');
            case 'r3_one_4201':
                return lowerMsg.includes('r3') && lowerMsg.includes('4201') && lowerMsg.includes('exactly one');
            case 'r3_morning_required':
                return lowerMsg.includes('r3') && lowerMsg.includes('morning clinic');
            case 'r4_morning_required':
                return lowerMsg.includes('r4') && lowerMsg.includes('morning clinic');
            case 'r4_tuesday_teaching':
                return lowerMsg.includes('teaching') && lowerMsg.includes('tuesday');
            case 'r4_travel_restriction':
                return lowerMsg.includes('旅遊門診') && (lowerMsg.includes('monday') || lowerMsg.includes('friday'));
            case 'r4_fixed_schedule':
                return lowerMsg.includes('r4') && lowerMsg.includes('fixed schedule');
            case 'no_double_booking':
                return lowerMsg.includes('double-booked');
            case 'all_rooms_filled':
                return lowerMsg.includes('empty') || lowerMsg.includes('required room');
            case 'no_full_day':
                return lowerMsg.includes('morning and afternoon');
            case '4201_restriction':
                return lowerMsg.includes('4201') && (lowerMsg.includes('r4') || lowerMsg.includes('r1'));
            case '4204_r1_only':
                return lowerMsg.includes('4204') && !lowerMsg.includes('r1');
            default:
                return false;
        }
    });
}

// Helper function to get person info
function getPersonInfo(personId, statistics) {
    // Try to get name from global data if available
    if (typeof collectFormData === 'function') {
        try {
            const formData = collectFormData();
            const level = personId.substring(0, 2);
            if (formData.personnel && formData.personnel[level] && formData.personnel[level][personId]) {
                return {
                    name: formData.personnel[level][personId].name || ''
                };
            }
        } catch (e) {
            // Ignore errors
        }
    }
    
    return {
        name: ''
    };
}