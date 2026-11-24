<template>
  <div class="board-page">
    <div ref="root" class="pp board-body">
      <header class="board-bar">
        <div class="board-title-box">
          <h1 id="board-title" class="board-title">Доска</h1>
          <span id="status" class="pill pill-gray" role="status" aria-live="polite">Подключение…</span>
          <span id="saved-state" class="saved-state" data-tip-pos="bottom" hidden></span>
        </div>
        <div id="board-meter" class="meter" role="img" hidden>
          <span class="meter-bar"><span class="meter-fill"></span></span>
          <span id="board-meter-value" class="meter-value">0%</span>
        </div>
        <div id="peers" class="peers" aria-label="Участники"></div>
        <span id="peer-count" class="peer-count" hidden></span>
        <div id="bar-actions" class="header-actions">
          <div class="menu-wrap">
            <button id="file-btn" class="ibtn bordered" type="button" aria-haspopup="menu" aria-expanded="false"
                    aria-controls="file-menu" aria-label="Файл доски" data-tip="Файл доски" data-tip-pos="left"></button>
            <div id="file-menu" class="menu" role="menu" hidden>
              <button id="menu-export" type="button" role="menuitem">Выгрузить доску (.json)</button>
              <button id="menu-import" type="button" role="menuitem">Загрузить из файла…</button>
              <button id="menu-png" type="button" role="menuitem">Сохранить картинку (PNG)</button>
            </div>
            <input id="import-file" type="file" accept=".json,application/json" hidden>
          </div>
          <button id="chat-btn" class="ibtn bordered chat-btn" type="button" aria-controls="chat" aria-expanded="false"
                  aria-label="Чат" data-tip="Чат" data-tip-pos="left"><span id="chat-badge" class="badge" hidden></span></button>
          <button id="invite-btn" class="btn primary" type="button" aria-label="Пригласить"><span class="btn-label">Пригласить</span></button>
        </div>
      </header>

      <div class="board-main">
        <div id="stage" class="stage">
          <canvas id="canvas" aria-label="Холст доски" role="img"></canvas>
          <div id="cursors" class="cursors" aria-hidden="true"></div>
          <div id="toolbar" class="toolbar" role="toolbar" aria-label="Инструменты"></div>
          <div id="zoombar" class="zoombar">
            <button id="zoom-value" class="zoom-value" type="button" data-tip="Сбросить масштаб" aria-label="Сбросить масштаб">100%</button>
          </div>
          <div id="board-message" class="board-message" hidden>
            <div class="form-card">
              <h2 id="board-message-title">Доска не найдена</h2>
              <p id="board-message-text" class="muted">Проверьте код или выберите доску из списка.</p>
              <div class="row"><router-link class="btn primary" to="/boards">К списку досок</router-link></div>
            </div>
          </div>
        </div>

        <aside id="chat" class="chat" aria-labelledby="chat-title" hidden>
          <div class="chat-head">
            <h2 id="chat-title">Чат</h2>
            <span id="chat-meter" class="chat-meter" data-tip-pos="bottom" hidden></span>
            <span class="grow"></span>
            <span id="chat-close-slot"></span>
          </div>
          <div id="chat-list" class="chat-list" role="log" aria-live="polite" aria-relevant="additions" tabindex="0"></div>
          <p id="chat-empty" class="chat-empty muted">Сообщений пока нет. Напишите первым.</p>
          <form id="chat-form" class="chat-form" novalidate>
            <span id="chat-count" class="chat-count" aria-live="polite" hidden></span>
            <textarea id="chat-input" rows="1" maxlength="1000" placeholder="Сообщение… (Enter — отправить)"
                      aria-label="Сообщение" autocomplete="off"></textarea>
            <span id="chat-send-slot"></span>
          </form>
        </aside>
      </div>

      <dialog id="name-dialog" class="dialog" aria-labelledby="name-dialog-title">
        <form id="name-form" method="dialog">
          <h2 id="name-dialog-title">Вход на доску</h2>
          <p class="muted">Введите код доски, который сообщил репетитор. Другие участники увидят ваше имя из профиля.</p>
          <label hidden>Имя <input id="name-input" type="text" maxlength="32" autocomplete="nickname"></label>
          <label id="code-field" hidden>Код доски
            <input id="code-input" type="text" maxlength="64" autocomplete="off" autocapitalize="characters" spellcheck="false">
          </label>
          <p id="join-error" class="error-text" role="alert" hidden></p>
          <div class="row">
            <button id="join-submit" class="btn primary" type="submit">Войти</button>
            <router-link class="btn ghost" to="/boards">Отмена</router-link>
          </div>
        </form>
      </dialog>

      <dialog id="invite-dialog" class="dialog" aria-labelledby="invite-dialog-title">
        <form method="dialog">
          <h2 id="invite-dialog-title">Пригласить участников</h2>
          <p class="muted">Ученик открывает раздел «Доски» и вводит код. Код видите только вы.</p>
          <label>Адрес <input id="invite-site" type="text" readonly></label>
          <label>Код входа <input id="invite-code" type="text" class="code-value" readonly></label>
          <p id="invite-unknown" class="error-text" hidden>Код неизвестен на этом устройстве: смените его, чтобы получить новый.</p>
          <div class="row">
            <button id="invite-copy" class="btn primary" type="button">Копировать приглашение</button>
            <button class="btn ghost" value="close">Закрыть</button>
          </div>
          <div class="dialog-section">
            <label>Сменить код <span class="hint">старый сразу перестанет действовать, участники на доске останутся</span>
              <input id="new-code-input" type="text" maxlength="64" autocomplete="off" spellcheck="false"
                     placeholder="свой код от 6 символов или пусто — сгенерировать">
            </label>
            <div class="row"><button id="change-code" class="btn" type="button">Сменить код</button></div>
          </div>
        </form>
      </dialog>

      <dialog id="kick-dialog" class="dialog" aria-labelledby="kick-dialog-title">
        <form method="dialog">
          <h2 id="kick-dialog-title">Исключить «<span id="kick-name"></span>»?</h2>
          <p class="muted">Участник будет отключён и не сможет войти снова. Код доски сменится, новый код увидите только вы.
            Остальные участники останутся на доске.</p>
          <div class="row">
            <button class="btn danger" value="kick">Исключить</button>
            <button class="btn ghost" value="cancel" autofocus>Отмена</button>
          </div>
        </form>
      </dialog>

      <dialog id="clear-dialog" class="dialog" aria-labelledby="clear-dialog-title">
        <form method="dialog">
          <h2 id="clear-dialog-title">Очистить доску?</h2>
          <p class="muted">Рисунки исчезнут у всех участников. Отменить это нельзя.</p>
          <div class="row">
            <button class="btn danger" value="clear">Очистить</button>
            <button class="btn ghost" value="cancel" autofocus>Отмена</button>
          </div>
        </form>
      </dialog>

      <dialog id="import-dialog" class="dialog" aria-labelledby="import-dialog-title">
        <form method="dialog">
          <h2 id="import-dialog-title">Загрузить доску из файла</h2>
          <p id="import-summary" class="muted"></p>
          <p class="muted">Изменения сразу увидят все участники.</p>
          <div class="row">
            <button class="btn primary" value="append">Добавить к рисунку</button>
            <button class="btn danger" value="replace">Заменить всё</button>
            <button class="btn ghost" value="cancel">Отмена</button>
          </div>
        </form>
      </dialog>
    </div>
  </div>
</template>

<script setup>
// Страница доски во весь экран. Разметка — здесь, поведение — перенесённый клиент ui/legacy/board.
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { boardSocketToken, uploadBoardFile } from '../../../logic/actions/index.js'
import { startBoard } from '../../legacy/board/board.js'
import '../../legacy/board/board.css'

const route = useRoute()
const router = useRouter()
const root = ref(null)
let destroy = null

function mount() {
  destroy?.()
  destroy = startBoard({
    boardId: String(route.params.id),
    root: root.value,
    host: {
      token: (opts) => boardSocketToken(opts),
      importBoard: (id, body) => uploadBoardFile(id, body),
      navigate: (path) => router.push(path),
    },
  })
}

onMounted(mount)
watch(() => route.params.id, (id, old) => { if (id && id !== old) router.go(0) })
onBeforeUnmount(() => { destroy?.(); destroy = null })
</script>
