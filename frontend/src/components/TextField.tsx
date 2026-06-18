import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";

interface BaseProps {
  id: string;
  label: string;
  hint?: ReactNode;
  hasValue?: boolean;
  wrapperClassName?: string;
}

interface InputFieldProps extends BaseProps, Omit<InputHTMLAttributes<HTMLInputElement>, "id"> {
  multiline?: false;
}

interface TextareaFieldProps extends BaseProps, Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "id"> {
  multiline: true;
}

interface SelectFieldProps extends BaseProps, Omit<SelectHTMLAttributes<HTMLSelectElement>, "id"> {
  multiline?: false;
  options: ReactNode;
}

type TextFieldProps = InputFieldProps | TextareaFieldProps | (SelectFieldProps & { multiline?: undefined });

export function TextField(props: TextFieldProps) {
  const { id, label, hint, hasValue, wrapperClassName, multiline, ...rest } = props;
  const showFloated = hasValue ?? false;

  function wrapperClass(floated: boolean): string {
    return [
      "text-field",
      floated ? "text-field--has-value" : "",
      wrapperClassName ?? "",
    ]
      .filter(Boolean)
      .join(" ");
  }

  if (multiline) {
    const textareaProps = rest as TextareaHTMLAttributes<HTMLTextAreaElement>;
    const floated = showFloated || Boolean(textareaProps.value);
    return (
      <div className={wrapperClass(floated)}>
        <textarea
          id={id}
          className={`text-field__input${textareaProps.className ? ` ${textareaProps.className}` : ""}`}
          placeholder=" "
          {...textareaProps}
        />
        <label className="text-field__label" htmlFor={id}>
          {label}
        </label>
        {hint && <p className="text-field__hint">{hint}</p>}
      </div>
    );
  }

  if ("options" in props) {
    const selectProps = rest as SelectHTMLAttributes<HTMLSelectElement>;
    const floated = showFloated || Boolean(selectProps.value);
    return (
      <div className={wrapperClass(floated)}>
        <select
          id={id}
          className="text-field__input"
          {...selectProps}
        >
          {props.options}
        </select>
        <label className="text-field__label" htmlFor={id}>
          {label}
        </label>
        {hint && <p className="text-field__hint">{hint}</p>}
      </div>
    );
  }

  const inputProps = rest as InputHTMLAttributes<HTMLInputElement>;
  const floated = showFloated || Boolean(inputProps.value);
  return (
    <div className={wrapperClass(floated)}>
      <input
        id={id}
        className="text-field__input"
        placeholder=" "
        {...inputProps}
      />
      <label className="text-field__label" htmlFor={id}>
        {label}
      </label>
      {hint && <p className="text-field__hint">{hint}</p>}
    </div>
  );
}
