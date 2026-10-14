"use strict";

// 할 일 화면. 외부 라이브러리 없이 동작한다.
// 서버에서 온 문자열(제목, 오류 문구)은 항상 textContent로만 화면에 넣는다.
(() => {
  const STORAGE_KEY = "todoApiKey";
  const REQUEST_TIMEOUT_MS = 15000;
  const FILTER_QUERY = { all: "", pending: "?completed=false", completed: "?completed=true" };

  const MESSAGES = {
    keyRequired: "API 키를 입력해 주세요.",
    keyWrong: "API 키가 올바르지 않습니다.",
    keyChanged: "API 키가 올바르지 않거나 바뀌었습니다. 다시 입력해 주세요.",
    keyNotPersisted:
      "이 브라우저에서는 키를 저장할 수 없어 탭을 닫으면 다시 입력해야 합니다.",
    titleRequired: "제목을 입력해 주세요.",
    addedButHidden: "추가했습니다. 현재 필터에서는 보이지 않습니다.",
    alreadyDeleted: "이미 삭제된 할 일입니다.",
    network:
      "서버에 연결할 수 없습니다. 서버가 실행 중인지 확인한 뒤 새로고침을 눌러 주세요.",
    serverError: "서버에서 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    emptyAll: "할 일이 없습니다. 위에서 추가해 보세요.",
    emptyFiltered: "해당하는 할 일이 없습니다.",
  };

  // --- KeyStore: 키 값을 다루는 곳은 여기와 callApi뿐이다 ---

  const keyStore = (() => {
    let memoryKey = null;

    function read() {
      try {
        return window.localStorage.getItem(STORAGE_KEY) ?? memoryKey;
      } catch {
        return memoryKey;
      }
    }

    // 브라우저 저장소에 저장했으면 true, 메모리에만 보관했으면 false
    function write(key) {
      memoryKey = key;
      try {
        window.localStorage.setItem(STORAGE_KEY, key);
        return true;
      } catch {
        return false;
      }
    }

    function clear() {
      memoryKey = null;
      try {
        window.localStorage.removeItem(STORAGE_KEY);
      } catch {
        // 저장소를 쓸 수 없는 환경에서는 메모리 값만 지우면 된다.
      }
    }

    return { read, write, clear };
  })();

  // --- ApiClient: 모든 호출이 이 함수를 지난다 ---
  // 결과는 세 가지뿐이다: ok(데이터), rejected(상태 코드와 서버 문구), network(연결 실패/시간 초과)

  async function callApi(method, path, { key, body } = {}) {
    const headers = { "X-API-Key": key ?? keyStore.read() ?? "" };
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    const init = { method, headers, signal: controller.signal, cache: "no-store" };
    if (body !== undefined) {
      headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(body);
    }

    try {
      const response = await fetch(path, init);
      if (response.status === 204) {
        return { kind: "ok", data: null };
      }
      let payload = null;
      try {
        payload = await response.json();
      } catch (error) {
        if (error.name === "AbortError") {
          return { kind: "network" };
        }
      }
      if (response.ok && payload !== null) {
        return { kind: "ok", data: payload };
      }
      const message = payload?.error?.message;
      const retryAfter = Number.parseInt(response.headers.get("Retry-After") ?? "", 10);
      return {
        kind: "rejected",
        status: response.status,
        message: typeof message === "string" ? message : null,
        retryAfter: Number.isFinite(retryAfter) ? retryAfter : null,
      };
    } catch {
      return { kind: "network" };
    } finally {
      window.clearTimeout(timer);
    }
  }

  // --- AppState ---

  const state = {
    filter: "all",
    todos: [],
    busyIds: new Set(),
    adding: false,
    submittingKey: false,
    listRequestSeq: 0,
    pendingDelete: null,
  };

  const byId = (id) => document.getElementById(id);
  const el = {
    notice: byId("notice"),
    noticeLabel: byId("notice-label"),
    noticeMessage: byId("notice-message"),
    noticeClose: byId("notice-close"),
    starting: byId("starting"),
    keyView: byId("key-view"),
    keyForm: byId("key-form"),
    keyInput: byId("key-input"),
    keySubmit: byId("key-submit"),
    listView: byId("list-view"),
    addForm: byId("add-form"),
    addInput: byId("add-input"),
    addSubmit: byId("add-submit"),
    filterButtons: Array.from(document.querySelectorAll("[data-filter]")),
    refresh: byId("refresh-button"),
    clearKey: byId("clear-key-button"),
    loading: byId("loading"),
    list: byId("todo-list"),
    empty: byId("empty-state"),
    itemTemplate: byId("todo-item-template"),
    dialog: byId("confirm-dialog"),
    confirmTitle: byId("confirm-title"),
    confirmCancel: byId("confirm-cancel"),
    confirmOk: byId("confirm-ok"),
  };

  // --- 화면 갱신 ---

  function showNotice(kind, text) {
    el.notice.dataset.kind = kind;
    // 오류는 즉시, 정보는 차분하게 화면 낭독기에 알린다.
    el.notice.setAttribute("role", kind === "error" ? "alert" : "status");
    el.noticeLabel.textContent = kind === "error" ? "오류" : "안내";
    el.noticeMessage.textContent = text;
    el.notice.hidden = false;
  }

  function clearNotice() {
    el.notice.hidden = true;
    el.noticeMessage.textContent = "";
  }

  function showView(view) {
    el.starting.hidden = true;
    el.keyView.hidden = view !== "key";
    el.listView.hidden = view !== "list";
  }

  function renderFilters() {
    for (const button of el.filterButtons) {
      button.setAttribute("aria-pressed", String(button.dataset.filter === state.filter));
    }
  }

  function renderEmptyState() {
    const isEmpty = state.todos.length === 0 && el.loading.hidden;
    el.empty.textContent = state.filter === "all" ? MESSAGES.emptyAll : MESSAGES.emptyFiltered;
    el.empty.hidden = !isEmpty;
  }

  function setLoading(isLoading) {
    el.loading.hidden = !isLoading;
    el.refresh.setAttribute("aria-disabled", String(isLoading));
    renderEmptyState();
  }

  // 서버의 UTC 시각(예: 2026-10-14T07:25:02.123456Z)을 이 브라우저 시간대의 날짜로 바꾼다.
  // 형식이 다르면 null을 돌려주고 화면에는 "-"로 보인다.
  const UTC_TIMESTAMP = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?Z$/;

  function localDateParts(timestamp) {
    const match = typeof timestamp === "string" ? UTC_TIMESTAMP.exec(timestamp) : null;
    if (!match) {
      return null;
    }
    // 브라우저마다 소수점 아래 자릿수 처리가 달라 밀리초(3자리)까지만 넘긴다.
    const millis = (match[2] ?? "").slice(0, 3).padEnd(3, "0");
    const date = new Date(`${match[1]}.${millis}Z`);
    if (Number.isNaN(date.getTime())) {
      return null;
    }
    return [
      String(date.getFullYear()).padStart(4, "0"),
      String(date.getMonth() + 1).padStart(2, "0"),
      String(date.getDate()).padStart(2, "0"),
    ];
  }

  function fillDate(timeElement, timestamp) {
    const parts = localDateParts(timestamp);
    timeElement.textContent = parts ? parts.join("/") : "-";
    if (parts) {
      timeElement.dateTime = parts.join("-");
    } else {
      timeElement.removeAttribute("datetime");
    }
  }

  function fillItem(item, todo) {
    const titleId = `todo-${todo.id}-title`;
    const datesId = `todo-${todo.id}-dates`;
    item.dataset.todoId = String(todo.id);
    item.dataset.completed = String(todo.completed);
    const checkbox = item.querySelector(".todo-checkbox");
    checkbox.checked = todo.completed;
    // 체크 상자의 이름은 제목, 날짜는 보조 설명으로 읽히게 한다.
    checkbox.setAttribute("aria-labelledby", titleId);
    checkbox.setAttribute("aria-describedby", datesId);
    const title = item.querySelector(".todo-title");
    title.id = titleId;
    title.textContent = todo.title;
    item.querySelector(".todo-dates").id = datesId;
    fillDate(item.querySelector(".todo-created"), todo.created_at);
    // 완료: 날짜(기록이 없던 예전 항목은 "-"), 미완료: 글자 없이 자리만 남긴다.
    const completedDate = item.querySelector('[data-testid="todo-item-completed-date"]');
    completedDate.classList.toggle("is-blank", !todo.completed);
    const completedTime = item.querySelector(".todo-completed");
    if (todo.completed) {
      fillDate(completedTime, todo.completed_at);
    } else {
      completedTime.textContent = "";
      completedTime.removeAttribute("datetime");
    }
    item
      .querySelector(".button-danger")
      .setAttribute("aria-label", `삭제: ${todo.title}`);
  }

  function createItem(todo) {
    const item = el.itemTemplate.content.firstElementChild.cloneNode(true);
    fillItem(item, todo);
    return item;
  }

  function findItem(id) {
    return el.list.querySelector(`[data-todo-id="${id}"]`);
  }

  function renderList() {
    const fragment = document.createDocumentFragment();
    for (const todo of state.todos) {
      fragment.append(createItem(todo));
    }
    el.list.replaceChildren(fragment);
    renderEmptyState();
  }

  function matchesFilter(todo) {
    if (state.filter === "pending") {
      return !todo.completed;
    }
    if (state.filter === "completed") {
      return todo.completed;
    }
    return true;
  }

  function removeTodo(id) {
    state.todos = state.todos.filter((todo) => todo.id !== id);
    const item = findItem(id);
    if (!item) {
      return;
    }
    // 포커스가 사라지는 항목 안에 있었다면 가까운 곳으로 옮긴다.
    const hadFocus = item.contains(document.activeElement);
    const neighbor = item.nextElementSibling ?? item.previousElementSibling;
    item.remove();
    if (hadFocus) {
      (neighbor?.querySelector(".todo-checkbox") ?? el.addInput).focus();
    }
    renderEmptyState();
  }

  function replaceTodo(updated) {
    state.todos = state.todos.map((todo) => (todo.id === updated.id ? updated : todo));
    const item = findItem(updated.id);
    if (item) {
      fillItem(item, updated);
    }
  }

  function setBusy(id, isBusy) {
    if (isBusy) {
      state.busyIds.add(id);
    } else {
      state.busyIds.delete(id);
    }
    findItem(id)?.setAttribute("aria-busy", String(isBusy));
  }

  function resetListState() {
    state.filter = "all";
    state.todos = [];
    state.busyIds.clear();
    state.listRequestSeq += 1; // 진행 중이던 목록 응답은 버린다.
    renderFilters();
    el.loading.hidden = true;
    renderList();
    el.addInput.value = "";
  }

  function showKeyView() {
    resetListState();
    showView("key");
    el.keyInput.focus();
  }

  function showListView(todos) {
    state.todos = todos;
    renderFilters();
    renderList();
    showView("list");
    el.addInput.focus();
  }

  // --- 실패 처리: 응답 종류별 안내 (어떤 실패도 화면을 멈추지 않는다) ---

  function describeRejection(result) {
    if (result.status === 429) {
      const wait = result.retryAfter ? ` (약 ${result.retryAfter}초 후)` : "";
      return `${result.message ?? "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요."}${wait}`;
    }
    if (result.status >= 500) {
      return result.message ?? MESSAGES.serverError;
    }
    return result.message ?? `예상하지 못한 응답입니다 (상태 코드 ${result.status}).`;
  }

  function handleFailure(result, { whileSubmittingKey = false } = {}) {
    if (result.kind === "network") {
      showNotice("error", MESSAGES.network);
      return;
    }
    if (result.status === 401) {
      if (whileSubmittingKey) {
        showNotice("error", MESSAGES.keyWrong);
        return;
      }
      // 저장된 키가 더 이상 맞지 않는다. 지우고 다시 입력받는다.
      keyStore.clear();
      showKeyView();
      showNotice("error", MESSAGES.keyChanged);
      return;
    }
    showNotice("error", describeRejection(result));
  }

  // --- 동작 ---

  // 목록을 불러온다. 더 나중에 보낸 요청이 있으면 이 응답은 버리고 null을 돌려준다.
  async function requestTodos(options) {
    const seq = ++state.listRequestSeq;
    setLoading(true);
    const result = await callApi("GET", `/todos${FILTER_QUERY[state.filter]}`, options);
    if (seq !== state.listRequestSeq) {
      return null;
    }
    setLoading(false);
    return result;
  }

  async function start() {
    if (!keyStore.read()) {
      showKeyView();
      return;
    }
    const result = await requestTodos();
    if (!result) {
      return;
    }
    if (result.kind === "ok") {
      showListView(result.data.todos);
      return;
    }
    const keyRejected = result.kind === "rejected" && result.status === 401;
    if (!keyRejected) {
      showListView([]);
    }
    handleFailure(result);
  }

  async function submitKey() {
    const key = el.keyInput.value.trim();
    if (!key) {
      showNotice("error", MESSAGES.keyRequired);
      el.keyInput.focus();
      return;
    }
    if (state.submittingKey) {
      return;
    }
    state.submittingKey = true;
    el.keySubmit.disabled = true;
    state.filter = "all";
    const result = await requestTodos({ key });
    state.submittingKey = false;
    el.keySubmit.disabled = false;
    if (!result) {
      return;
    }
    if (result.kind !== "ok") {
      handleFailure(result, { whileSubmittingKey: true });
      el.keyInput.select();
      return;
    }
    // 서버가 받아들인 키만 저장한다.
    const persisted = keyStore.write(key);
    el.keyInput.value = "";
    showListView(result.data.todos);
    if (persisted) {
      clearNotice();
    } else {
      showNotice("info", MESSAGES.keyNotPersisted);
    }
  }

  function clearKey() {
    keyStore.clear();
    clearNotice();
    showKeyView();
  }

  async function reloadTodos() {
    const result = await requestTodos();
    if (!result) {
      return false;
    }
    if (result.kind !== "ok") {
      handleFailure(result); // 실패하면 화면의 목록은 그대로 둔다.
      return false;
    }
    state.todos = result.data.todos;
    renderList();
    clearNotice();
    return true;
  }

  async function changeFilter(filter) {
    if (filter === state.filter) {
      return;
    }
    const previous = state.filter;
    state.filter = filter;
    renderFilters();
    const loaded = await reloadTodos();
    // 불러오지 못했으면 필터 표시를 되돌려 목록과 어긋나지 않게 한다.
    if (!loaded && state.filter === filter && !el.listView.hidden) {
      state.filter = previous;
      renderFilters();
      renderEmptyState();
    }
  }

  async function addTodo() {
    const title = el.addInput.value.trim();
    if (!title) {
      showNotice("error", MESSAGES.titleRequired);
      el.addInput.focus();
      return;
    }
    if (state.adding) {
      return;
    }
    state.adding = true;
    el.addSubmit.disabled = true;
    const result = await callApi("POST", "/todos", { body: { title } });
    state.adding = false;
    el.addSubmit.disabled = false;

    if (result.kind !== "ok") {
      handleFailure(result); // 입력한 내용은 지우지 않는다.
      return;
    }
    el.addInput.value = "";
    el.addInput.focus();
    if (matchesFilter(result.data)) {
      state.todos = [result.data, ...state.todos];
      el.list.prepend(createItem(result.data));
      renderEmptyState();
      clearNotice();
    } else {
      showNotice("info", MESSAGES.addedButHidden);
    }
  }

  async function toggleTodo(id, checkbox) {
    const todo = state.todos.find((candidate) => candidate.id === id);
    if (!todo || state.busyIds.has(id)) {
      // 처리 중인 항목은 다시 누를 수 없다. 방금 누른 것을 되돌린다.
      checkbox.checked = !checkbox.checked;
      return;
    }
    const completed = checkbox.checked;
    // 누르는 즉시 반영하고, 서버가 거부하면 되돌린다.
    findItem(id).dataset.completed = String(completed);
    setBusy(id, true);
    const result = await callApi("PATCH", `/todos/${id}`, { body: { completed } });
    setBusy(id, false);

    if (result.kind === "ok") {
      if (matchesFilter(result.data)) {
        replaceTodo(result.data);
      } else {
        removeTodo(id);
      }
      clearNotice();
      return;
    }
    if (result.kind === "rejected" && result.status === 404) {
      removeTodo(id);
      showNotice("info", MESSAGES.alreadyDeleted);
      return;
    }
    replaceTodo(todo);
    handleFailure(result);
  }

  function askDelete(id) {
    const todo = state.todos.find((candidate) => candidate.id === id);
    if (!todo || state.busyIds.has(id)) {
      return;
    }
    state.pendingDelete = todo;
    el.confirmTitle.textContent = todo.title;
    el.dialog.showModal();
    el.confirmCancel.focus();
  }

  async function confirmDelete() {
    const todo = state.pendingDelete;
    el.dialog.close();
    if (!todo) {
      return;
    }
    setBusy(todo.id, true);
    const result = await callApi("DELETE", `/todos/${todo.id}`);
    setBusy(todo.id, false);

    if (result.kind === "ok") {
      removeTodo(todo.id);
      clearNotice();
      return;
    }
    if (result.kind === "rejected" && result.status === 404) {
      removeTodo(todo.id);
      showNotice("info", MESSAGES.alreadyDeleted);
      return;
    }
    handleFailure(result);
  }

  // --- 이벤트 연결 ---

  function todoIdOf(target) {
    const item = target.closest("[data-todo-id]");
    return item ? Number(item.dataset.todoId) : null;
  }

  el.keyForm.addEventListener("submit", (event) => {
    event.preventDefault();
    submitKey();
  });

  el.addForm.addEventListener("submit", (event) => {
    event.preventDefault();
    addTodo();
  });

  for (const button of el.filterButtons) {
    button.addEventListener("click", () => changeFilter(button.dataset.filter));
  }

  el.refresh.addEventListener("click", () => {
    if (el.loading.hidden) {
      reloadTodos();
    }
  });

  el.clearKey.addEventListener("click", clearKey);
  el.noticeClose.addEventListener("click", clearNotice);

  el.list.addEventListener("change", (event) => {
    const id = todoIdOf(event.target);
    if (id !== null && event.target.matches(".todo-checkbox")) {
      toggleTodo(id, event.target);
    }
  });

  el.list.addEventListener("click", (event) => {
    const button = event.target.closest(".button-danger");
    const id = button ? todoIdOf(button) : null;
    if (id !== null) {
      askDelete(id);
    }
  });

  el.confirmCancel.addEventListener("click", () => el.dialog.close());
  el.confirmOk.addEventListener("click", confirmDelete);

  // 창 바깥(배경)을 누르면 취소한다. Esc는 브라우저가 처리한다.
  el.dialog.addEventListener("click", (event) => {
    if (event.target !== el.dialog) {
      return;
    }
    const box = el.dialog.getBoundingClientRect();
    const inside =
      event.clientX >= box.left &&
      event.clientX <= box.right &&
      event.clientY >= box.top &&
      event.clientY <= box.bottom;
    if (!inside) {
      el.dialog.close();
    }
  });

  el.dialog.addEventListener("close", () => {
    state.pendingDelete = null;
  });

  start();
})();
