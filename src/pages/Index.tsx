import ClearFrameLogo from "@/components/ClearFrameLogo";
import PromptInput from "@/components/PromptInput";

const Index = () => {
  return (
    <main className="min-h-screen bg-background flex flex-col items-center p-12">
      <div className="flex flex-col items-center gap-8 w-full max-w-4xl mt-20">
        {/* Logo */}
        <ClearFrameLogo />

        {/* Divider */}
        <div className="w-full h-px bg-divider" />

        {/* Prompt Input */}
        <div className="w-full mt-4">
          <PromptInput />
        </div>
      </div>
    </main>
  );
};

export default Index;
