import { CheckCircle2, XCircle, AlertCircle, Flame, ListChecks, BarChart3, Copy } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { MetricScale } from "@/components/MetricScale";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface EnhancedPayload {
  averages?: Record<string, number>;
  coverage?: Record<string, any>;
  categories?: Record<string, any>;
  propaganda?: Record<string, any>;
  topPropaganda?: { technique: string; count: number }[];
  articles?: Array<{
    title: string;
    source: string;
    url: string;
    biasCategory?: string;
    credibilityTier?: string;
    sourceType?: string;
    politicalLean?: number;
    overallBias?: number;
    emotionalManipulation?: number;
    sensationalism?: number;
    propagandaScore?: number;
    factualLanguage?: number;
    framing?: number;
    techniques?: string[];
  }>;
  recommendations?: string[];
  narrativeComparison?: any;
}

interface FactCheckResultProps {
  result: {
    status: "true" | "false" | "partial";
    confidence: number;
    explanation: string;
    sources: { title: string; url: string }[];
    metrics?: {
      omission_score?: number;
      sentiment_delta?: number;
      loaded_language_score?: number;
      censorship_radar_metric?: number;
      source_diversity?: number;
    };
    enhanced?: EnhancedPayload;
    raw?: any;
  };
  grandmaMode?: boolean;
}

export const FactCheckResult = ({ result, grandmaMode = false }: FactCheckResultProps) => {
  const getStatusIcon = () => {
    switch (result.status) {
      case "true":
        return (
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-6 h-6 text-accent" />
            <span className="text-2xl">✅</span>
          </div>
        );
      case "false":
        return (
          <div className="flex items-center gap-2">
            <XCircle className="w-6 h-6 text-destructive" />
            <span className="text-2xl">❌</span>
          </div>
        );
      case "partial":
        return (
          <div className="flex items-center gap-2">
            <AlertCircle className="w-6 h-6 text-primary" />
            <span className="text-2xl">⚠️</span>
          </div>
        );
    }
  };

  const getStatusText = () => {
    switch (result.status) {
      case "true":
        return "Verified";
      case "false":
        return "False";
      case "partial":
        return "Partially True";
    }
  };

  const getStatusColor = () => {
    switch (result.status) {
      case "true":
        return "bg-accent/20 text-accent border-accent/30";
      case "false":
        return "bg-destructive/20 text-destructive border-destructive/30";
      case "partial":
        return "bg-primary/20 text-primary border-primary/30";
    }
  };

  const enhanced = result.enhanced;

  return (
    <div className="w-full relative z-10 animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-6 fade-in-delayed">
      <div className="glass-card rounded-2xl p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {getStatusIcon()}
            <h3 className="text-xl font-black text-white">General Verdict</h3>
          </div>
          <Badge className={getStatusColor()}>
            {result.confidence}% confidence
          </Badge>
        </div>
        <div className="mt-4">
          <p className="font-semibold text-foreground">{getStatusText()}</p>
          <p className="text-sm mt-2 text-foreground/70 leading-relaxed">{result.explanation}</p>
        </div>
      </div>

      {!grandmaMode && (
        <Accordion type="multiple" className="space-y-4">
          <AccordionItem value="metrics">
            <AccordionTrigger>
              <div className="flex items-center gap-2">
                <span>📊</span> Included Metrics
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <p className="text-xs text-foreground/70 mb-4">Deterministic summaries of source classes: emphasis, omissions, lexical tone.</p>
              <div className="grid grid-cols-1 gap-4">
                <div className="glass-card rounded-2xl p-4">
                  <MetricScale value={result.metrics?.omission_score ?? 0} label="Omission Score" />
                </div>
                <div className="glass-card rounded-2xl p-4">
                  <MetricScale value={result.metrics?.sentiment_delta ?? 0} label="Sentiment Delta" />
                </div>
                <div className="glass-card rounded-2xl p-4">
                  <MetricScale value={result.metrics?.loaded_language_score ?? 0} label="Loaded Language" />
                </div>
                <div className="glass-card rounded-2xl p-4">
                  <MetricScale value={result.metrics?.censorship_radar_metric ?? 0} label="Censorship Radar" />
                </div>
                <div className="glass-card rounded-2xl p-4">
                  <MetricScale value={result.metrics?.source_diversity ?? 0} label="Source Diversity" min={0} max={10} />
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>

          {result.sources.length > 0 && (
            <AccordionItem value="sources">
              <AccordionTrigger>
                <div className="flex items-center gap-2">
                  <span>📚</span> Sources
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="grid grid-cols-3 gap-3">
                  {result.sources.slice(0, 3).map((source, index) => (
                    <div key={index} className="glass-card rounded-2xl p-4">
                      <h5 className="text-xs font-bold text-foreground line-clamp-2">{source.title}</h5>
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-block mt-3 px-3 py-1 rounded-md bg-primary/20 text-white font-bold text-xs hover:bg-primary/30 transition-colors"
                      >
                        View →
                      </a>
                    </div>
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>
          )}

          {enhanced && (
            <AccordionItem value="analysis">
              <AccordionTrigger>
                <div className="flex items-center gap-2">
                  <BarChart3 className="w-4 h-4" /> Analysis
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-8">
                  {/* Bias Landscape */}
                  <div className="space-y-3">
                    <h4 className="text-sm font-bold text-foreground uppercase tracking-wider flex items-center gap-2">
                      <BarChart3 className="w-4 h-4" /> Bias Landscape
                    </h4>
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                      <div className="glass-card rounded-xl p-4"><MetricScale value={enhanced.averages?.political_lean ?? 0} label="Avg Political Lean" /></div>
                      <div className="glass-card rounded-xl p-4"><MetricScale value={enhanced.averages?.emotional_manipulation ?? 0} label="Emotional Manipulation" /></div>
                      <div className="glass-card rounded-xl p-4"><MetricScale value={enhanced.averages?.sensationalism ?? 0} label="Sensationalism" /></div>
                      <div className="glass-card rounded-xl p-4"><MetricScale value={enhanced.averages?.propaganda ?? 0} label="Propaganda" /></div>
                      <div className="glass-card rounded-xl p-4"><MetricScale value={enhanced.averages?.factual_language ?? 0} label="Factual Language" min={0} max={100} /></div>
                      <div className="glass-card rounded-xl p-4"><MetricScale value={enhanced.averages?.overall_bias ?? 0} label="Overall Bias Score" /></div>
                    </div>
                  </div>

                  {/* Propaganda Techniques */}
                  {enhanced.topPropaganda && enhanced.topPropaganda.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="text-sm font-bold text-foreground uppercase tracking-wider flex items-center gap-2">
                        <Flame className="w-4 h-4" /> Propaganda Techniques
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {enhanced.topPropaganda.map(t => (
                          <Badge key={t.technique} className="bg-orange-500/20 text-orange-300 border-orange-500/30">
                            {t.technique} ({t.count})
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Source Composition */}
                  <div className="space-y-3">
                    <h4 className="text-sm font-bold text-foreground uppercase tracking-wider flex items-center gap-2">
                      <ListChecks className="w-4 h-4" /> Source Composition
                    </h4>
                    <div className="grid md:grid-cols-2 gap-4">
                      <div className="glass-card rounded-xl p-4">
                        <h5 className="text-xs font-bold mb-2 text-foreground">Credibility Tiers</h5>
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(enhanced.categories?.credibility_tiers || {}).map(([tier, count]) => (
                            <Badge key={tier} className="bg-primary/15 text-primary border-primary/30">{tier}: {count as number}</Badge>
                          ))}
                        </div>
                      </div>
                      <div className="glass-card rounded-xl p-4">
                        <h5 className="text-xs font-bold mb-2 text-foreground">Source Types</h5>
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(enhanced.categories?.source_types || {}).map(([stype, count]) => (
                            <Badge key={stype} className="bg-secondary/15 text-secondary border-secondary/30">{stype}: {count as number}</Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Recommendations */}
                  {enhanced.recommendations && enhanced.recommendations.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="text-sm font-bold text-foreground uppercase tracking-wider flex items-center gap-2">🧭 Recommendations</h4>
                      <ul className="text-xs list-disc pl-5 space-y-1 text-foreground/80">
                        {enhanced.recommendations.slice(0, 5).map((r, i) => <li key={i}>{r}</li>)}
                      </ul>
                    </div>
                  )}

                  {/* Articles Table */}
                  {enhanced.articles && enhanced.articles.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="text-sm font-bold text-foreground uppercase tracking-wider flex items-center gap-2">📰 Article Bias Details</h4>
                      <ScrollArea className="h-[320px] glass-card rounded-xl p-2">
                        <table className="w-full text-xs">
                          <thead className="text-left sticky top-0 bg-background/60 backdrop-blur">
                            <tr className="text-[10px] uppercase tracking-wide text-foreground/70">
                              <th className="p-2">Title</th>
                              <th className="p-2">Source</th>
                              <th className="p-2">Bias</th>
                              <th className="p-2">Cred</th>
                              <th className="p-2">Lean</th>
                              <th className="p-2">Overall</th>
                              <th className="p-2">Propaganda</th>
                              <th className="p-2">Emotional</th>
                              <th className="p-2">Factual</th>
                              <th className="p-2">Techniques</th>
                            </tr>
                          </thead>
                          <tbody>
                            {enhanced.articles.map((a, i) => (
                              <tr key={i} className="border-b border-white/5 hover:bg-white/5">
                                <td className="p-2 max-w-[220px]">
                                  <a href={a.url} target="_blank" rel="noopener noreferrer" className="font-semibold text-foreground hover:underline line-clamp-2">
                                    {a.title || 'Untitled'}
                                  </a>
                                </td>
                                <td className="p-2 whitespace-nowrap">{a.source}</td>
                                <td className="p-2 whitespace-nowrap">{a.biasCategory}</td>
                                <td className="p-2 whitespace-nowrap">{a.credibilityTier}</td>
                                <td className="p-2 whitespace-nowrap">{Math.round(a.politicalLean ?? 0)}</td>
                                <td className="p-2 whitespace-nowrap">{Math.round(a.overallBias ?? 0)}</td>
                                <td className="p-2 whitespace-nowrap">{Math.round(a.propagandaScore ?? 0)}</td>
                                <td className="p-2 whitespace-nowrap">{Math.round(a.emotionalManipulation ?? 0)}</td>
                                <td className="p-2 whitespace-nowrap">{Math.round(a.factualLanguage ?? 0)}</td>
                                <td className="p-2">
                                  <div className="flex flex-wrap gap-1">
                                    {(a.techniques || []).slice(0, 3).map(t => (
                                      <Badge key={t} className="bg-purple-500/20 text-purple-300 border-purple-400/30">{t}</Badge>
                                    ))}
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </ScrollArea>
                    </div>
                  )}
                </div>
              </AccordionContent>
            </AccordionItem>
          )}

          {/* Raw JSON payload for inspection */}
          {result.raw && (
            <AccordionItem value="raw">
              <AccordionTrigger asChild>
                <div className="flex justify-between items-center w-full">
                  <span>🔎 Raw API Payload</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      navigator.clipboard.writeText(JSON.stringify(result.raw, null, 2));
                    }}
                    className="flex items-center gap-1 px-2 py-1 text-xs bg-primary/20 hover:bg-primary/30 rounded-md transition-colors"
                  >
                    <Copy className="w-3 h-3" />
                    Copy
                  </button>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <ScrollArea className="h-[360px]">
                  <pre className="text-[11px] leading-snug whitespace-pre-wrap break-words p-3 bg-black/40 rounded-lg border border-white/10">
                    {JSON.stringify(result.raw, null, 2)}
                  </pre>
                </ScrollArea>
              </AccordionContent>
            </AccordionItem>
          )}
        </Accordion>
      )}
    </div>
  );
};
