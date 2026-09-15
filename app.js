let fallbackRevealTimer = null;
let openTgGoalSent = false;
let claimBusy = false;
let claimDone = false;

// Must match landing/index.html Yandex.Metrika counter id
const METRIKA_COUNTER_ID = 110355947;

function setClaimButtonsDisabled(disabled) {
    document.querySelectorAll('.cta-clean').forEach(function (btn) {
        btn.disabled = disabled;
    });
}

function getMetrikaClientId(timeoutMs) {
    return new Promise(function (resolve) {
        if (typeof ym !== 'function') {
            resolve('');
            return;
        }
        var settled = false;
        var timer = setTimeout(function () {
            if (!settled) {
                settled = true;
                resolve('');
            }
        }, timeoutMs);
        try {
            ym(METRIKA_COUNTER_ID, 'getClientID', function (clientID) {
                if (!settled) {
                    settled = true;
                    clearTimeout(timer);
                    resolve(clientID || '');
                }
            });
        } catch (e) {
            clearTimeout(timer);
            resolve('');
        }
    });
}

function clearFallbackTimer() {
    if (fallbackRevealTimer) {
        clearTimeout(fallbackRevealTimer);
        fallbackRevealTimer = null;
    }
}

function setClaimStatus(message, kind, linkUrl) {
    const statusEl = document.getElementById('claimStatus');
    if (!statusEl) return;
    clearFallbackTimer();
    statusEl.replaceChildren();
    if (!message) {
        statusEl.className = 'claim-status claim-toast hidden';
        return;
    }
    statusEl.className = 'claim-status claim-toast' + (kind ? ' ' + kind : '');
    statusEl.appendChild(document.createTextNode(message));
    if (linkUrl) {
        statusEl.appendChild(document.createTextNode(' '));
        const a = document.createElement('a');
        a.href = linkUrl;
        a.rel = 'noopener';
        a.textContent = linkUrl;
        statusEl.appendChild(a);
    }
}

function reachGoal(name) {
    if (typeof ym !== 'function') return;
    try {
        ym(METRIKA_COUNTER_ID, 'reachGoal', name);
    } catch (e) {
        /* analytics must not block */
    }
}

/** https://t.me/+HASH → tg://join?invite=HASH; fallback keeps the https URL. */
function inviteOpenUrls(httpsUrl) {
    var m = String(httpsUrl || '').match(
        /(?:t\.me|telegram\.me)\/(?:\+|joinchat\/)([A-Za-z0-9_-]+)/
    );
    return {
        primary: m ? ('tg://join?invite=' + m[1]) : httpsUrl,
        fallback: httpsUrl
    };
}

function openInvite(httpsUrl) {
    if (!httpsUrl) return;
    var urls = inviteOpenUrls(httpsUrl);
    if (!openTgGoalSent) {
        openTgGoalSent = true;
        reachGoal('miidas_join_click');
    }
    // Schedule https fallback before navigate so a cancelled timer is intentional if we leave.
    clearFallbackTimer();
    fallbackRevealTimer = setTimeout(function () {
        fallbackRevealTimer = null;
        setClaimStatus(
            'Если Telegram не открылся (из РФ нужен VPN):',
            'info',
            urls.fallback
        );
    }, 1500);
    window.location.href = urls.primary;
}

async function claimAccess(event) {
    if (claimBusy || claimDone) return;
    claimBusy = true;
    const btn = event.currentTarget;
    const source = btn.dataset.source || '';
    setClaimStatus('Резервируем группу…', 'info');
    setClaimButtonsDisabled(true);
    openTgGoalSent = false;

    try {
        const ymClientId = await getMetrikaClientId(500);
        let body = '';
        if (source) {
            body = 'source=' + encodeURIComponent(source);
        }
        if (ymClientId) {
            body += (body ? '&' : '') + 'ym_client_id=' + encodeURIComponent(ymClientId);
        }
        const resp = await fetch('/cgi/claim', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: body
        });
        const data = await resp.json();

        if (data.invite_link) {
            claimDone = true;
            setClaimStatus('');
            openInvite(data.invite_link);
            return;
        }
        if (data.error) {
            setClaimStatus(data.message || data.error, 'error');
        } else {
            setClaimStatus('Неизвестная ошибка. Попробуйте позже.', 'error');
        }
    } catch (e) {
        setClaimStatus('Ошибка соединения. Попробуйте позже.', 'error');
    }
    claimBusy = false;
    setClaimButtonsDisabled(false);
}

// Event listeners (replaces onclick attributes)
document.addEventListener('DOMContentLoaded', function () {
    const claimBtns = document.querySelectorAll('.cta-clean');
    claimBtns.forEach(function (btn) {
        btn.addEventListener('click', claimAccess);
    });

    // — Mobile hamburger navigation —
    var navToggle = document.querySelector('.nav-toggle');
    var navLinks = document.getElementById('nav-links');

    function closeNav() {
        if (!navToggle) return;
        navToggle.setAttribute('aria-expanded', 'false');
        if (navLinks) navLinks.classList.remove('open');
    }

    if (navToggle && navLinks) {
        navToggle.addEventListener('click', function () {
            var expanded = navToggle.getAttribute('aria-expanded') === 'true';
            navToggle.setAttribute('aria-expanded', String(!expanded));
            navLinks.classList.toggle('open', !expanded);
        });
        navLinks.querySelectorAll('a').forEach(function (link) {
            link.addEventListener('click', closeNav);
        });
        window.addEventListener('resize', function () {
            if (window.innerWidth > 720) closeNav();
        });
    }

    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // — MockupEngine — sequential frame playback with status replacement —
    // frames: [{ type, text, label?, time?, delay }]
    // type: 'user' | 'status' | 'result' | 'typing'

    const MOCKUP_DATA = {
        upd: [
            { type: 'user', text: 'Сделай УПД для ООО «Вектор». Услуги разработки за июнь, сумма та же.', time: '14:15', delay: 0 },
            { type: 'typing', delay: 2000 },
            { type: 'status', text: '⏳ Ищу действующую форму УПД 2026...', label: 'МИИДАС', time: '14:15', delay: 3600 },
            { type: 'status', text: '⏳ Подставляю реквизиты ООО «Вектор» и наши данные из истории чата...', label: 'МИИДАС', time: '14:15', delay: 5200 },
            { type: 'result', text: '📝 <strong>Черновик УПД сформирован</strong><br>• Покупатель: ООО «Вектор» (ИНН 7701234567)<br>• Услуга: Разработка ПО за июнь<br>• Сумма: <strong>150 000₽</strong> (без НДС)<br><span class="tg-dim">Реквизиты и ИНН взяты из договора в истории чата.</span>', buttons: ['Скачать PDF', 'Изменить', 'Готово'], label: 'МИИДАС · УПД', time: '14:16', delay: 6800 },
            { type: 'user', text: 'Скачать PDF', answer: 0, time: '14:16', delay: 10800 },
            { type: 'typing', delay: 12000 },
            { type: 'status', text: '⏳ Готовлю PDF для подписи в вашем ЭДО...', label: 'МИИДАС', time: '14:16', delay: 13600 },
            { type: 'result', text: '✅ <strong>PDF готов</strong><br>Файл можно загрузить в Диадок / СБИС и подписать.<br><br><span class="tg-dim">⚠️ Проверьте суммы и реквизиты перед подписью — подписываете вы.</span>', label: 'МИИДАС · готово', time: '14:17', delay: 15200 },
        ],
        usn: [
            { type: 'user', text: 'Посчитай налог за 2 квартал', time: '10:00', delay: 0 },
            { type: 'typing', delay: 2000 },
            { type: 'status', text: '⏳ Подключаюсь к банку для анализа поступлений...', label: 'МИИДАС', time: '10:00', delay: 3600 },
            { type: 'status', text: '⏳ Сверяю доходы по выписке с вашим режимом УСН...', label: 'МИИДАС', time: '10:00', delay: 5200 },
            { type: 'result', text: '🧮 <strong>Расчёт налога УСН за II квартал</strong><br>Вижу в профиле: <strong>ИП Иванов (УСН 6% «Доходы»)</strong><br>• Доходы по банку: 1 200 000₽<br>• Расчётный налог: 72 000₽<br>• Уплаченные страховые взносы: −22 000₽<br>💵 <strong>Итого к уплате: 50 000₽</strong><br><br><span class="tg-dim">Взносы учтены по факту списания со счёта.</span>', buttons: ['Подготовить платежку', 'Сформировать декларацию', 'Детали расчёта'], label: 'МИИДАС · УСН', time: '10:01', delay: 6800 },
            { type: 'user', text: 'Подготовить платежку', answer: 0, time: '10:01', delay: 10800 },
            { type: 'typing', delay: 12000 },
            { type: 'status', text: '⏳ Готовлю черновик платёжного поручения...', label: 'МИИДАС', time: '10:01', delay: 13600 },
            { type: 'result', text: '📄 <strong>Черновик платёжки на 50 000₽ готов</strong><br>Назначение: Авансовый платёж по УСН за II квартал 2026 г.<br>Получатель: УФК по Тульской области (Единый налоговый счёт)<br><br><span class="tg-success">👉 Можно подписать в интернет-банке.</span><br><br><span class="tg-dim">⚠️ Это черновик. Проверьте реквизиты перед отправкой платежа в ФНС.</span>', label: 'МИИДАС · готово', time: '10:02', delay: 15200 },
        ],
        journal: [
            { type: 'user', text: 'Загрузи выписку за июнь', time: '10:15', delay: 0 },
            { type: 'typing', delay: 2000 },
            { type: 'status', text: '⏳ Подключаюсь к банку...', label: 'МИИДАС', time: '10:15', delay: 3600 },
            { type: 'status', text: '✅ Загрузил выписку: 347 операций', label: 'МИИДАС', time: '10:16', delay: 5200 },
            { type: 'bot', text: 'Для сверки нужен ваш внутренний журнал учета. Скиньте Excel-файл или выгрузку из 1С.', label: 'МИИДАС', time: '10:17', delay: 6800 },
            { type: 'user', text: '[Файл] Июнь_учет.xlsx', time: '10:18', delay: 10800 },
            { type: 'typing', delay: 12400 },
            { type: 'result', text: '📊 Найдено <span class="tg-highlight">12 расхождений</span><br>3 дубля · 5 пропусков · 4 неверные суммы<br><span class="tg-success">✅ Месяц закрыт за 5 мин</span>', label: 'МИИДАС · готово', time: '10:19', delay: 14000 },
        ],
        payment: [
            { type: 'user', text: 'Разложи расходы за июнь по категориям', time: '11:30', delay: 0 },
            { type: 'typing', delay: 2000 },
            { type: 'status', text: '⏳ Анализирую выписку: 412 операций...', label: 'МИИДАС', time: '11:30', delay: 3600 },
            { type: 'status', text: '✅ Разношу по статьям...', label: 'МИИДАС', time: '11:31', delay: 5200 },
            { type: 'result', text: 'Разнесено:<br>🏢 Поставщики: 187 · 💰 Зарплата: 24<br>🏠 Аренда: 6 · 📢 Маркетинг: 31 · 📋 Налоги: 15 · 🔧 Прочие: 42', label: 'МИИДАС · разноска', time: '11:31', delay: 6800 },
            { type: 'user', text: 'Сколько нераспознано?', time: '11:31', delay: 10800 },
            { type: 'typing', delay: 12000 },
            { type: 'status', text: '⚠️ 17 операций на 38 200₽. Разбираю...', label: 'МИИДАС', time: '11:31', delay: 13600 },
            { type: 'result', text: '«Оплата по сч. 458» — 5 400₽<br><span class="tg-dim">Выберите категорию:</span>', buttons: ['Хостинг', 'ПО / лицензии', 'Прочее'], label: 'МИИДАС · вопрос', time: '11:32', delay: 15200 },
            { type: 'user', text: 'Хостинг', answer: 0, time: '11:32', delay: 19200 },
            { type: 'typing', delay: 20400 },
            { type: 'result', text: '✅ 412 операций на 1 622 600₽ успешно распределены по категориям (точность <span class="tg-highlight">96%</span>)<br>⚠️ Найдено 2 дубликата оплат на 22 400₽!', label: 'МИИДАС · готово', time: '11:33', delay: 22000 },
        ],
        pnl: [
            { type: 'user', text: 'Какая прибыль за июнь?', time: '09:00', delay: 0 },
            { type: 'typing', delay: 2000 },
            { type: 'status', text: '⏳ Загружаю данные из банка...', label: 'МИИДАС', time: '09:00', delay: 3600 },
            { type: 'status', text: '✅ Данные получены. Считаю P&L...', label: 'МИИДАС', time: '09:01', delay: 5200 },
            { type: 'result', text: '📊 <strong>P&L — Июнь</strong><br>Доходы: <strong>1 890 000₽</strong><br>Расходы: <strong>1 251 234₽</strong><br>Чистая прибыль: <strong style="color:var(--success);">638 766₽ (33.8%)</strong>', label: 'МИИДАС · P&L', time: '09:01', delay: 6800 },
            { type: 'result', text: '⚠️ Рентабельность ↓ 2.1% — рост себестоимости на 6%<br>🟡 Маркетинг +40%, ROI снизился<br>🟢 Дебиторка −18%', label: 'МИИДАС · тренды', time: '09:02', delay: 8400 },
        ],
        data: [
            { type: 'user', text: 'Сверь данные из банка и 1С за июнь', time: '14:00', delay: 0 },
            { type: 'typing', delay: 2000 },
            { type: 'status', text: '⏳ Подключаюсь к банку...', label: 'МИИДАС', time: '14:00', delay: 3600 },
            { type: 'status', text: '✅ Выписка загружена: 411 операций', label: 'МИИДАС', time: '14:01', delay: 5200 },
            { type: 'status', text: '⏳ Загружаю данные из 1С...', label: 'МИИДАС', time: '14:01', delay: 6800 },
            { type: 'status', text: '✅ 385 проводок. Сравниваю...', label: 'МИИДАС · сверка', time: '14:02', delay: 8400 },
            { type: 'result', text: '🔍 <span class="tg-highlight">17 расхождений</span>:<br>• 8 в банке, нет в 1С (912 000₽)<br>• 5 в 1С, нет в банке (143 000₽)<br>• 4 суммы не совпадают', label: 'МИИДАС · результат', time: '14:02', delay: 10000 },
            { type: 'result', text: '🔴 Налог УСН 187 000₽ списан с банка, но не проведён в 1С.<br><span class="tg-highlight">Крайний срок уплаты — сегодня!</span>', label: 'МИИДАС · критично', time: '14:03', delay: 11600 },
        ],
        debtors: [
            { type: 'user', text: 'Кто мне должен?', time: '08:45', delay: 0 },
            { type: 'typing', delay: 2000 },
            { type: 'status', text: '⏳ Загружаю данные по дебиторам...', label: 'МИИДАС', time: '08:45', delay: 3600 },
            { type: 'status', text: '✅ 38 записей на 1 240 000₽. Группирую по срокам...', label: 'МИИДАС', time: '08:46', delay: 5200 },
            { type: 'result', text: '📊 <strong>Структура дебиторки</strong><br>🟢 0–30 дн: 540 000₽ (18)<br>🟡 31–60 дн: 380 000₽ (10)<br>🟠 61–90 дн: 210 000₽ (6)<br>🔴 90+ дн: 110 000₽ (4)', label: 'МИИДАС · дебиторка', time: '08:46', delay: 6800 },
            { type: 'result', text: '⚠️ ООО «СтройИнвест» — <span class="tg-highlight">127 000₽</span><br>94 дня просрочки. Шанс взыскания: 11%<br><span class="tg-dim">Рекомендация: претензия сегодня</span>', label: 'МИИДАС · критично', time: '08:47', delay: 8400 },
            { type: 'user', text: 'Настрой автонапоминания', time: '08:47', delay: 12400 },
            { type: 'typing', delay: 13600 },
            { type: 'result', text: '✅ График напоминаний настроен<br>📅 День 3 — ООО «Снабженец» (завтра)<br>📅 День 14 — ИП Соколов<br>📅 День 30 — Волга-Строй<br>📅 День 60 — СтройИнвест', label: 'МИИДАС · готово', time: '08:48', delay: 15200 },
            { type: 'result', text: 'Хотите посмотреть текст напоминания перед отправкой?<br><span class="tg-dim">Можно отредактировать или отправить как есть</span>', label: 'МИИДАС', time: '08:48', delay: 16800 },
            { type: 'user', text: 'Покажи, что отправишь.', time: '08:48', delay: 20800 },
            { type: 'typing', delay: 22000 },
            { type: 'result', text: 'Предлагаю:<br><span class="tg-dim">— — — — — — — —</span><br>Иван, добрый день!<br>Счёт №458 (34 000₽) ждёт оплаты — срок был 15-го июня.<br>Нужна ли рассрочка?<br><span class="tg-dim">— — — — — — — —</span>', buttons: ['Отправить', 'Редактировать', 'Отмена'], label: 'МИИДАС · предпросмотр', time: '08:49', delay: 23600 },
            { type: 'user', text: 'Отправить', answer: 0, time: '08:49', delay: 27600 },
            { type: 'typing', delay: 28800 },
            { type: 'result', text: '📬 <strong>Напоминания отправлены 5 клиентам</strong><br>✅ Все прочитали в Telegram<br>✅ 2 ответили: «оплатим на этой неделе»<br>✅ 1 оплатил прямо сейчас (18 000₽)<br><br><span class="tg-dim">Я работаю, пока вы спите 😴→🤖→💰</span>', label: 'МИИДАС · через 3 дня', time: '08:45', delay: 30400 },
        ],
        suppliers: [
            { type: 'user', text: '[Переслал PDF — счёт ТехноСнаб №458]', time: '15:20', delay: 0 },
            { type: 'typing', delay: 2000 },
            { type: 'status', text: '⏳ Распознаю счёт...', label: 'МИИДАС', time: '15:20', delay: 3600 },
            { type: 'status', text: '✅ Распознан: ООО «ТехноСнаб»<br>Счёт №458 · 93 400₽ · срок 25.07', label: 'МИИДАС', time: '15:20', delay: 5200 },
            { type: 'status', text: '⏳ Сверяю с договорами и историей...', label: 'МИИДАС', time: '15:20', delay: 6800 },
            { type: 'result', text: '✅ С договором совпадает<br>⚠️ <span class="tg-highlight">Дубль найден!</span> — этот счёт уже загружен 28.06', label: 'МИИДАС · сверка', time: '15:21', delay: 8400 },
            { type: 'user', text: 'Сохрани исправленный, удали дубль', time: '15:21', delay: 12400 },
            { type: 'typing', delay: 13600 },
            { type: 'result', text: '✅ Счёт №458 (93 400₽) — сохранён как исправленный<br>🗑️ Дубль от 28.06 — удалён', label: 'МИИДАС', time: '15:21', delay: 15200 },
            { type: 'result', text: '📋 <strong>Сегодня на контроле</strong><br>24 счета на 1 870 000₽<br>🔔 Напоминания: 09.07 — Яндекс · 10.07 — Снабженец<br>⚠️ Просрочено: 3 счета', label: 'МИИДАС · дашборд', time: '15:22', delay: 16800 },
        ],
    };

    function MockupEngine(container) {
        this.container = container;
        this.timers = [];
    }
    MockupEngine.prototype.play = function (frames) {
        this.stop();
        var self = this;
        this.container.innerHTML = '';
        var inner = document.createElement('div');
        inner.className = 'tg-inner';
        var eng = document.createElement('div');
        eng.className = 'tg-engine';
        var perm = document.createElement('div');
        perm.className = 'tg-permanent';
        var slot = document.createElement('div');
        slot.className = 'tg-status-slot';
        eng.appendChild(perm);
        eng.appendChild(slot);
        inner.appendChild(eng);
        this.container.appendChild(inner);
        frames.forEach(function (f) {
            var delay = reduceMotion ? 0 : f.delay;
            var t = setTimeout(function () { self._show(f, perm, slot); }, delay);
            self.timers.push(t);
        });
    };
    MockupEngine.prototype._show = function (frame, perm, slot) {
        if (frame.type === 'typing') {
            if (reduceMotion) return;
            slot.innerHTML = '<div class="tg-typing tg-fade-in"><span></span><span></span><span></span></div>';
            this._autoscroll();
            return;
        }
        var isStatus = frame.type === 'status';
        var isBot = frame.type === 'bot';
        var cls = isStatus || isBot || frame.type === 'result' ? 'tg-msg tg-msg-bot' : 'tg-msg tg-msg-user';
        var msg = document.createElement('div');
        msg.className = cls + (reduceMotion ? '' : ' tg-fade-in');
        msg.innerHTML = (frame.label ? '<span class="tg-label">' + frame.label + '</span>' : '')
            + frame.text + '<div class="tg-time">' + (frame.time || '') + '</div>';
        // Render inline buttons
        if (frame.type === 'result' && frame.buttons) {
            var btnsDiv = document.createElement('div');
            btnsDiv.className = 'tg-buttons';
            btnsDiv.dataset.answers = JSON.stringify(frame.buttons);
            frame.buttons.forEach(function (txt) {
                var b = document.createElement('button');
                b.className = 'tg-btn';
                b.textContent = txt;
                b.addEventListener('click', function () {
                    if (btnsDiv._resolved) return;
                    btnsDiv.innerHTML = '<span class="tg-choice">✅ ' + txt + '</span>';
                    btnsDiv._resolved = true;
                });
                btnsDiv.appendChild(b);
            });
            msg.appendChild(btnsDiv);
        }
        if (isStatus) {
            slot.innerHTML = '';
            slot.appendChild(msg);
        } else if (isBot) {
            perm.appendChild(msg);
        } else {
            if (frame.type === 'result') slot.innerHTML = '';
            var skipUser = false;
            if (frame.type === 'user' && frame.answer !== undefined) {
                var botMsgs = perm.querySelectorAll('.tg-msg-bot');
                for (var i = botMsgs.length - 1; i >= 0; i--) {
                    var btns = botMsgs[i].querySelector('.tg-buttons');
                    if (btns) {
                        if (!btns._resolved) {
                            var answers = JSON.parse(btns.dataset.answers || '[]');
                            var answer = answers[frame.answer] || '';
                            btns.innerHTML = '<span class="tg-choice">✅ ' + answer + '</span>';
                            btns._resolved = true;
                        }
                        skipUser = true;
                        break;
                    }
                }
            }
            if (!skipUser) perm.appendChild(msg);
        }
        this._autoscroll();
    };
    MockupEngine.prototype._autoscroll = function () {
        var s = this.container;
        if (!s) return;
        s.scrollTo({ top: s.scrollHeight, behavior: reduceMotion ? 'auto' : 'smooth' });
    };
    MockupEngine.prototype.stop = function () {
        this.timers.forEach(function (t) { clearTimeout(t); });
        this.timers = [];
    };

    var engines = {};
    var PRIMARY_PAINS = ['upd', 'usn', 'pnl'];
    var MORE_PAINS = ['journal', 'payment', 'data', 'debtors', 'suppliers'];

    function playPainMockup(name) {
        if (!MOCKUP_DATA[name]) return;
        var panel = document.getElementById('pain-' + name);
        if (!panel) return;
        var body = panel.querySelector('.tg-body[data-mockup="' + name + '"]')
            || panel.querySelector('.tg-body[data-mockup]');
        if (!body) return;
        if (engines[name]) engines[name].stop();
        var eng = new MockupEngine(body);
        engines[name] = eng;
        eng.play(MOCKUP_DATA[name]);
    }

    function playPainList(names, staggerMs) {
        var step = reduceMotion ? 0 : (staggerMs || 0);
        names.forEach(function (name, i) {
            if (step === 0) {
                playPainMockup(name);
            } else {
                setTimeout(function () { playPainMockup(name); }, i * step);
            }
        });
    }

    // Primary panels always visible — play all on load
    if (document.querySelector('.pain-demo-primary .pain-panel') || document.getElementById('pain-journal')) {
        setTimeout(function () {
            playPainList(PRIMARY_PAINS, 180);
        }, reduceMotion ? 0 : 300);
    }

    var moreBtn = document.getElementById('painMoreBtn');
    var morePanels = document.getElementById('painMorePanels');
    if (moreBtn && morePanels) {
        moreBtn.addEventListener('click', function () {
            morePanels.removeAttribute('hidden');
            moreBtn.hidden = true;
            moreBtn.disabled = true;
            if (reduceMotion) {
                morePanels.classList.add('is-open');
                playPainList(MORE_PAINS, 180);
            } else {
                requestAnimationFrame(function () {
                    requestAnimationFrame(function () {
                        morePanels.classList.add('is-open');
                    });
                });
                playPainList(MORE_PAINS, 180);
            }
        });
    }
});

// Hero mockup: typing then bot messages
(function () {
    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var body = document.querySelector('.hero-mockup .tg-body');
    function completeHeroTyping() {
        var typing = document.getElementById('hero-typing');
        if (typing) typing.classList.add('done');
        if (body) {
            body.classList.remove('is-waiting');
            body.classList.add('animate');
        }
    }
    if (reduceMotion) {
        completeHeroTyping();
    } else {
        if (body) body.classList.add('is-waiting');
        setTimeout(completeHeroTyping, 1500);
    }
})();
