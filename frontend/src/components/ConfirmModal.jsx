import { useEffect, useRef } from "react";

// Our own confirm dialog (the spec rules out window.confirm). <dialog> handles focus and the backdrop.
export default function ConfirmModal({ title, children, confirmLabel, danger, busy, error, onConfirm, onCancel }) {
  const dialog = useRef(null);

  useEffect(() => {
    if (!dialog.current.open) dialog.current.showModal();
  }, []);

  return (
    <dialog
      ref={dialog}
      className="modal"
      onCancel={(e) => {
        e.preventDefault(); // Esc: let the parent unmount us
        onCancel();
      }}
    >
      <h2>{title}</h2>
      <div className="modal-body">{children}</div>
      {error && (
        <p className="notice notice-error" role="alert">
          {error}
        </p>
      )}
      <div className="modal-actions">
        <button className="btn" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button className={`btn ${danger ? "btn-danger" : "btn-primary"}`} onClick={onConfirm} disabled={busy}>
          {confirmLabel}
        </button>
      </div>
    </dialog>
  );
}
