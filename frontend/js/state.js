// ===========================
// state.js
// client-side small state
// ===========================
export const state = {
  currentUser: null,
  activeChatRoom: null,
  uploadedFiles: [],
  notices: [],
};

export function setCurrentUser(user) {
  state.currentUser = user;
}

export function addNotice(notice) {
  state.notices.push(notice);
}

export function addUploadedFile(file) {
  state.uploadedFiles.push(file);
}
