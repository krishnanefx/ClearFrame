import { useState, useEffect } from "react";
import { FactCheckInput } from "@/components/FactCheckInput";
import { FactCheckResult } from "@/components/FactCheckResult";
import { GrandmaCats } from "@/components/GrandmaCats";
import { GrandmaCat } from "@/components/GrandmaCat";

const Index = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [isResultShown, setIsResultShown] = useState(false);
  const [grandmaModeEnabled, setGrandmaModeEnabled] = useState(false);
  const [result, setResult] = useState<{
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
  } | null>(null);

  // Update document class for Grandma Mode color scheme
  useEffect(() => {
    if (grandmaModeEnabled) {
      document.documentElement.classList.add('grandma-mode');
    } else {
      document.documentElement.classList.remove('grandma-mode');
    }
  }, [grandmaModeEnabled]);

  const handleFactCheck = async (prompt: string) => {
    setIsLoading(true);
    setResult(null);

    try {
      // Call the backend API
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/api/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: prompt,
          max_results: 9,
          search_type: 'web',
          response_length: 'large',
          enable_advanced: false,
        }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();
      console.debug('[FactFlow] /api/analyze raw response:', data);

      // --- Enhanced mapping ---
      const biasAnalysis = data.bias_analysis || {}; // server structure
      const articles: any[] = biasAnalysis.articles || [];
      const aggregateStats = biasAnalysis.aggregate_stats || {};
      const avgScores = aggregateStats.average_scores || {};
      const coverage = aggregateStats.coverage_assessment || {};
      const categories = aggregateStats.category_breakdown || {};
      const propaganda = aggregateStats.propaganda_analysis || {};
      const recommendations: string[] = biasAnalysis.recommendations || [];
      const narrativeComparison = biasAnalysis.narrative_comparison || null;
      const topPropaganda = Object.entries(propaganda.top_techniques || {}).map(([k, v]) => ({ technique: k, count: v as number }));

      // Sources preview
      const sources = articles.slice(0, 3).map(a => ({
        title: a.title || 'Unknown',
        url: a.url || '#'
      }));

      // Confidence heuristic (can refine): combine credibility + inverse absolute bias
      const highCredCount = coverage.high_credibility_count || 0;
      const totalArticles = Math.max(1, articles.length);
      const credibilityScore = (highCredCount / totalArticles) * 100; // 0-100
      const overallBias = avgScores.overall_bias ?? 0; // -50..50 (expectation)
      const neutralityScore = 100 - Math.min(100, Math.abs(overallBias));
      const confidence = Math.round((credibilityScore * 0.6) + (neutralityScore * 0.4));

      // Verdict logic
      let status: "true" | "false" | "partial" = "partial";
      if (confidence >= 75 && Math.abs(overallBias) <= 15) status = 'true';
      else if (confidence < 45 || Math.abs(overallBias) >= 35) status = 'false';

      const explanation = biasAnalysis.overall_assessment || `Coverage across ${totalArticles} articles shows ${overallBias > 15 ? 'right' : overallBias < -15 ? 'left' : 'mixed'} leaning with ${highCredCount} high credibility sources.`;

      // Build enhanced view object
      const enhanced = {
        averages: avgScores,
        coverage,
        categories,
        propaganda,
        topPropaganda,
        articles: articles.map(a => ({
          title: a.title,
          source: a.source,
          url: a.url,
          biasCategory: a.classification?.bias_category,
          credibilityTier: a.classification?.credibility_tier,
          sourceType: a.classification?.source_type,
          politicalLean: a.bias_scores?.political_lean,
          overallBias: a.bias_scores?.overall_bias,
          emotionalManipulation: a.bias_scores?.emotional_manipulation,
          sensationalism: a.bias_scores?.sensationalism,
          propagandaScore: a.bias_scores?.propaganda,
          factualLanguage: a.bias_scores?.factual_language,
          framing: a.bias_scores?.balanced_framing,
          techniques: a.detected_features?.propaganda_techniques || [],
        })),
        recommendations,
        narrativeComparison,
      };

      console.debug('[FactFlow] enhanced mapping:', enhanced);

      setResult({
        status,
        confidence,
        explanation,
        sources,
        metrics: {
          omission_score: avgScores.omission_score || 0, // may not exist → fallback 0
          sentiment_delta: avgScores.sentiment_delta || 0, // may not exist → fallback 0
          loaded_language_score: avgScores.emotional_manipulation || 0,
          censorship_radar_metric: coverage.neutral_articles || 0, // placeholder for radar metric
          source_diversity: Object.keys(categories.source_types || {}).length || 0,
        },
        // @ts-ignore extend result shape without breaking existing component contract
        enhanced,
        // expose full backend payload for debug/inspect UI
        // @ts-ignore
        raw: data,
      });

      setIsResultShown(true);
    } catch (error) {
      console.error('Error analyzing claim:', error);
      // Optionally set an error state to show to the user
      setResult({
        status: "false",
        confidence: 0,
        explanation: "Failed to analyze claim. Please try again.",
        sources: [],
      });
      setIsResultShown(true);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-start p-4 relative page-opening fade-in overflow-y-auto pt-32">
      <div className="w-full max-w-3xl space-y-16 mx-auto">
        <div className="flex justify-center mb-8 fade-in -mt-4 w-full">
          <img
            src={grandmaModeEnabled ? "/grandma-logo.png" : "/clearframe-logo.png"}
            alt="ClearFrame"
            className="w-auto max-w-sm h-auto aspect-auto scale-[2]"
          />
          {grandmaModeEnabled && (
            <div className="fixed transition-transform duration-300 ease-out cursor-pointer hover:scale-110 hover:-translate-y-2" style={{ top: '190px', right: 'calc(48px + 24px)' }}>
              <img
                src="/grandma-cat.png"
                alt="Cute cat"
                className="w-32 h-auto"
              />
            </div>
          )}
        </div>

        <FactCheckInput
          onSubmit={handleFactCheck}
          isLoading={isLoading}
          grandmaModeEnabled={grandmaModeEnabled}
          onGrandmaModeChange={setGrandmaModeEnabled}
        />

        {result && <FactCheckResult result={result as any} grandmaMode={grandmaModeEnabled} />}
      </div>
    </div>
  );
};

export default Index;
