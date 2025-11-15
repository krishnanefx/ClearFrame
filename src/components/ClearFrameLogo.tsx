const ClearFrameLogo = () => {
  return (
    <div className="flex flex-col items-center gap-5">
      {/* Logo Icon */}
      <div className="relative w-20 h-20">
        {/* Outer rounded square frame with gradient */}
        <div className="absolute inset-0 border-[3px] border-logo-frame rounded-2xl shadow-md" />
        
        {/* Inner glow effect */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-accent/5 rounded-2xl" />
        
        {/* Inner elements - enhanced news icon */}
        <div className="absolute inset-0 flex items-center justify-center gap-2.5 p-4">
          {/* Left section - news column with header */}
          <div className="flex flex-col gap-1 items-center">
            <div className="w-2 h-2 bg-logo-accent rounded-sm" />
            <div className="w-2 h-8 bg-logo-inner rounded-full" />
          </div>
          
          {/* Right section - news text lines with variety */}
          <div className="flex flex-col gap-1.5 flex-1">
            <div className="w-full h-2 bg-logo-frame rounded-full" />
            <div className="w-4/5 h-1.5 bg-logo-inner rounded-full" />
            <div className="w-full h-1.5 bg-logo-inner rounded-full" />
            <div className="w-3/4 h-1.5 bg-muted-foreground/50 rounded-full" />
          </div>
        </div>
        
        {/* Corner accent */}
        <div className="absolute -top-1 -right-1 w-3 h-3 bg-logo-accent rounded-full shadow-sm" />
      </div>

      {/* Wordmark */}
      <h1 className="text-foreground font-bold text-base tracking-[0.25em] uppercase">
        ClearFrame
      </h1>
    </div>
  );
};

export default ClearFrameLogo;
