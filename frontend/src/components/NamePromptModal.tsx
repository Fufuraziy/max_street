import { useState, type FormEvent } from 'react';
import { Modal } from './ui';

interface NamePromptModalProps {
  onClose: () => void;
  onSubmit: (name: string) => void;
}

/** Гостевой режим (браузер вне MAX): спрашиваем имя, чтобы показать его в составе. */
export default function NamePromptModal({ onClose, onSubmit }: NamePromptModalProps) {
  const [name, setName] = useState('');
  const valid = name.trim().length >= 2;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (valid) onSubmit(name.trim());
  };

  return (
    <Modal
      title="Как вас зовут?"
      subtitle="Имя увидят другие участники сбора"
      onClose={onClose}
      footer={
        <button type="submit" form="name-form" className="btn-primary w-full" disabled={!valid}>
          Продолжить
        </button>
      }
    >
      <form id="name-form" onSubmit={submit}>
        <input
          autoFocus
          className="input"
          maxLength={64}
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Например, Артём"
          aria-label="Ваше имя"
        />
        <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
          Внутри MAX имя подставляется автоматически из профиля.
        </p>
      </form>
    </Modal>
  );
}
