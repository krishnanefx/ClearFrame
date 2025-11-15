import { useRef, useEffect } from "react";

const PromptInput = () => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleInput = (e: React.FormEvent<HTMLTextAreaElement>) => {
    const textarea = e.currentTarget;
    textarea.style.height = 'auto';
    textarea.style.height = `${textarea.scrollHeight}px`;
  };

  useEffect(() => {
    // Set initial height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, []);

  return (
    <div className="w-full max-w-3xl mx-auto">
      <div className="relative">
        <textarea
          ref={textareaRef}
          onInput={handleInput}
          placeholder="Type your report, ask for coverage ideas, or start drafting today…"
          className="w-full min-h-[60px] max-h-[400px] resize-none overflow-y-auto
                     bg-prompt-bg text-foreground
                     border border-prompt-border rounded-xl
                     px-[18px] py-[18px]
                     font-body text-base leading-relaxed
                     placeholder:text-muted-foreground
                     shadow-prompt
                     transition-shadow duration-200
                     focus:outline-none focus:shadow-prompt-focus
                     scrollbar-thin scrollbar-thumb-muted scrollbar-track-transparent"
          rows={1}
        />
      </div>
    </div>
  );
};

export default PromptInput;
