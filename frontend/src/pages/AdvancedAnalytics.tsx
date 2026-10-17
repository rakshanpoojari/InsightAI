import React, { useEffect, useState } from "react";
import { useDataset } from "../context/DatasetContext";
import { extractErrorMessage, getAnomalies, getForecast } from "../api/client";
import type { AnomalyResponse, ForecastResponse } from "../types/dataset";
import { LoadingSpinner } from "../components/LoadingState";
import AIForecastExplainer from "../components/AIForecastExplainer";
import {
  TrendingUp,
  AlertOctagon,
  Calendar,
  Sliders,
  Play,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  CheckCircle2,
} from "lucide-react";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ScatterChart,
  Scatter,
  Cell,
} from "recharts";

export default function AdvancedAnalytics() {
  const { activeDataset, loadSample } = useDataset();

  const [activeTab, setActiveTab] = useState<"anomalies" | "forecast">("anomalies");

  // Anomaly State
  const [anomalyCol, setAnomalyCol] = useState<string>("");
  const [contamination, setContamination] = useState<number>(0.05);
  const [anomalyData, setAnomalyData] = useState<AnomalyResponse | null>(null);
  const [isAnomalyLoading, setIsAnomalyLoading] = useState<boolean>(false);
  const [anomalyError, setAnomalyError] = useState<string | null>(null);

  // Forecast State
  const [forecastTarget, setForecastTarget] = useState<string>("");
  const [forecastDate, setForecastDate] = useState<string>("");
  const [horizon, setHorizon] = useState<number>(14);
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);
  const [isForecastLoading, setIsForecastLoading] = useState<boolean>(false);
  const [forecastError, setForecastError] = useState<string | null>(null);

  const numericCols = activeDataset?.columns.filter((c) => c.inferred_type === "numeric") || [];
  const dateCols = activeDataset?.columns.filter((c) => c.inferred_type === "datetime") || [];

  // Initialize dropdown defaults
  useEffect(() => {
    if (numericCols.length > 0 && !anomalyCol) {
      setAnomalyCol(numericCols[0].name);
    }
    if (numericCols.length > 0 && !forecastTarget) {
      setForecastTarget(numericCols[0].name);
    }
    if (dateCols.length > 0 && !forecastDate) {
      setForecastDate(dateCols[0].name);
    }
  }, [activeDataset]);

  const runAnomalyDetection = async () => {
    if (!activeDataset) return;
    setIsAnomalyLoading(true);
    setAnomalyError(null);
    try {
      const res = await getAnomalies(activeDataset.id, anomalyCol || undefined, contamination);
      setAnomalyData(res);
    } catch (e) {
      setAnomalyError(extractErrorMessage(e));
    } finally {
      setIsAnomalyLoading(false);
    }
  };

  const runForecasting = async () => {
    if (!activeDataset) return;
    setIsForecastLoading(true);
    setForecastError(null);
    try {
      const res = await getForecast(
        activeDataset.id,
        forecastTarget || undefined,
        forecastDate || undefined,
        horizon
      );
      setForecastData(res);
    } catch (e) {
      setForecastError(extractErrorMessage(e));
    } finally {
      setIsForecastLoading(false);
    }
  };

  // Run automatically on first mount if dataset exists
  useEffect(() => {
    if (activeDataset) {
      runAnomalyDetection();
      runForecasting();
    }
  }, [activeDataset?.id]);

  if (!activeDataset) {
    return (
      <div className="flex h-[70vh] flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-white p-12 text-center">
        <TrendingUp className="h-12 w-12 text-brand-500 mb-3" />
        <h2 className="text-lg font-bold text-slate-800">No Dataset Selected</h2>
        <p className="text-xs text-slate-400 max-w-sm mt-1 mb-5">
          Select or upload a dataset to run anomaly detection and predictive time-series forecasting.
        </p>
        <button
          onClick={loadSample}
          className="rounded-xl bg-brand-600 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-brand-700 transition"
        >
          Load Sample Dataset
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <TrendingUp className="h-6 w-6 text-brand-600" />
            Anomaly Detection & Predictive Forecasting
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Statistical Z-Score & IsolationForest outlier detection + regression time-series forecasting with 95% confidence intervals.
          </p>
        </div>

        {/* Tab Toggle */}
        <div className="flex rounded-xl bg-slate-200/70 p-1">
          <button
            onClick={() => setActiveTab("anomalies")}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold transition ${
              activeTab === "anomalies"
                ? "bg-white text-slate-900 shadow-2xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <AlertOctagon className="h-4 w-4 text-amber-600" />
            <span>Outlier & Anomaly Detection</span>
          </button>
          <button
            onClick={() => setActiveTab("forecast")}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold transition ${
              activeTab === "forecast"
                ? "bg-white text-slate-900 shadow-2xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Calendar className="h-4 w-4 text-blue-600" />
            <span>Time-Series Forecasting</span>
          </button>
        </div>
      </div>

      {/* TAB 1: ANOMALY DETECTION */}
      {activeTab === "anomalies" && (
        <div className="space-y-6">
          {/* Controls Bar */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Target Numeric Metric:</label>
                <select
                  value={anomalyCol}
                  onChange={(e) => setAnomalyCol(e.target.value)}
                  className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-800 font-semibold"
                >
                  {numericCols.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  Expected Contamination ({Math.round(contamination * 100)}%):
                </label>
                <input
                  type="range"
                  min="0.01"
                  max="0.15"
                  step="0.01"
                  value={contamination}
                  onChange={(e) => setContamination(parseFloat(e.target.value))}
                  className="w-32 accent-brand-600 cursor-pointer"
                />
              </div>
            </div>

            <button
              onClick={runAnomalyDetection}
              disabled={isAnomalyLoading}
              className="flex items-center gap-1.5 rounded-xl bg-brand-600 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-brand-700 disabled:opacity-50 transition"
            >
              <Play className="h-3.5 w-3.5" />
              <span>Detect Anomalies</span>
            </button>
          </div>

          {anomalyError && (
            <div className="rounded-xl bg-rose-50 p-4 text-sm text-rose-700 ring-1 ring-rose-200">
              {anomalyError}
            </div>
          )}

          {isAnomalyLoading ? (
            <LoadingSpinner message="Scanning dataset dimensions for statistical outliers..." />
          ) : anomalyData ? (
            <div className="space-y-6">
              {/* Summary Stats */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
                  <div className="text-xs font-semibold text-slate-400 uppercase">
                    Total Records Inspected
                  </div>
                  <div className="text-2xl font-black text-slate-900 mt-1">
                    {anomalyData.total_rows.toLocaleString()}
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
                  <div className="text-xs font-semibold text-slate-400 uppercase">
                    Anomalous Data Points
                  </div>
                  <div className="text-2xl font-black text-rose-600 mt-1">
                    {anomalyData.anomaly_count} ({anomalyData.anomaly_pct}%)
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
                  <div className="text-xs font-semibold text-slate-400 uppercase">
                    Target Evaluated
                  </div>
                  <div className="text-2xl font-black text-brand-700 mt-1">
                    {anomalyData.target_column}
                  </div>
                </div>
              </div>

              {/* Anomaly Chart */}
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
                <div className="border-b border-slate-100 pb-3 mb-4">
                  <h3 className="text-sm font-bold text-slate-800">
                    Distribution Plot with Outlier Flags
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Red points highlight records that deviate significantly from expected distribution bounds.
                  </p>
                </div>

                <div className="h-80 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis
                        dataKey="index"
                        name="Record #"
                        tick={{ fill: "#64748b", fontSize: 11 }}
                        tickLine={false}
                      />
                      <YAxis
                        dataKey={anomalyData.target_column}
                        name={anomalyData.target_column}
                        tick={{ fill: "#64748b", fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                      />
                      <Tooltip
                        cursor={{ strokeDasharray: "3 3" }}
                        content={({ payload }) => {
                          if (payload && payload.length > 0) {
                            const d = payload[0].payload;
                            return (
                              <div className="rounded-lg border border-slate-200 bg-white p-2.5 text-xs shadow-md">
                                <div className="font-bold text-slate-800">{d.label}</div>
                                <div className="text-slate-600">
                                  {anomalyData.target_column}:{" "}
                                  <strong>{d[anomalyData.target_column]?.toLocaleString()}</strong>
                                </div>
                                {d.is_anomaly && (
                                  <div className="mt-1 font-bold text-rose-600">
                                    Flagged as Outlier
                                  </div>
                                )}
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <Scatter data={anomalyData.chart_data}>
                        {anomalyData.chart_data.map((entry, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={entry.is_anomaly ? "#ef4444" : "#3b82f6"}
                            r={entry.is_anomaly ? 6 : 4}
                          />
                        ))}
                      </Scatter>
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Anomaly Table */}
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs space-y-3">
                <h3 className="text-sm font-bold text-slate-800">
                  Flagged Anomalous Records ({anomalyData.anomalies.length})
                </h3>
                {anomalyData.anomalies.length === 0 ? (
                  <div className="py-6 text-center text-xs text-slate-400">
                    No critical outliers detected within current contamination thresholds.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-xs text-left divide-y divide-slate-100">
                      <thead className="bg-slate-50 text-slate-600 font-semibold">
                        <tr>
                          <th className="px-4 py-2">Row #</th>
                          <th className="px-4 py-2">Z-Score</th>
                          <th className="px-4 py-2">Deviation Evidence</th>
                          <th className="px-4 py-2">Record Values</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {anomalyData.anomalies.map((a) => (
                          <tr key={a.index} className="hover:bg-slate-50">
                            <td className="px-4 py-2 font-mono font-bold text-slate-700">
                              #{a.index}
                            </td>
                            <td className="px-4 py-2">
                              <span className="rounded-md bg-rose-50 px-2 py-0.5 font-mono text-rose-700 font-bold">
                                {a.score}σ
                              </span>
                            </td>
                            <td className="px-4 py-2 text-slate-700 max-w-sm">
                              {a.reasons.join("; ")}
                            </td>
                            <td className="px-4 py-2 font-mono text-[11px] text-slate-500">
                              {Object.entries(a.row)
                                .slice(0, 4)
                                .map(([k, v]) => `${k}: ${v}`)
                                .join(", ")}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </div>
      )}

      {/* TAB 2: FORECASTING */}
      {activeTab === "forecast" && (
        <div className="space-y-6">
          {/* Controls Bar */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Target Metric:</label>
                <select
                  value={forecastTarget}
                  onChange={(e) => setForecastTarget(e.target.value)}
                  className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-800 font-semibold"
                >
                  {numericCols.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Date Dimension:</label>
                <select
                  value={forecastDate}
                  onChange={(e) => setForecastDate(e.target.value)}
                  className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-800 font-semibold"
                >
                  <option value="">Auto-Detect</option>
                  {activeDataset.columns.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name} ({c.inferred_type})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  Forecast Horizon: {horizon} periods
                </label>
                <input
                  type="range"
                  min="3"
                  max="30"
                  step="1"
                  value={horizon}
                  onChange={(e) => setHorizon(parseInt(e.target.value))}
                  className="w-32 accent-brand-600 cursor-pointer"
                />
              </div>
            </div>

            <button
              onClick={runForecasting}
              disabled={isForecastLoading}
              className="flex items-center gap-1.5 rounded-xl bg-brand-600 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-brand-700 disabled:opacity-50 transition"
            >
              <Play className="h-3.5 w-3.5" />
              <span>Generate Forecast</span>
            </button>
          </div>

          {forecastError && (
            <div className="rounded-xl bg-rose-50 p-4 text-sm text-rose-700 ring-1 ring-rose-200">
              {forecastError}
            </div>
          )}

          {isForecastLoading ? (
            <LoadingSpinner message="Fitting historical regression and projecting future intervals..." />
          ) : forecastData ? (
            <div className="space-y-6">
              {/* Metric Highlights */}
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
                  <div className="text-xs font-semibold text-slate-400 uppercase">
                    Trend Trajectory
                  </div>
                  <div className="flex items-center gap-1.5 text-xl font-black text-slate-900 mt-1">
                    {forecastData.metrics.trend_direction === "Upward" ? (
                      <ArrowUpRight className="h-5 w-5 text-emerald-600" />
                    ) : forecastData.metrics.trend_direction === "Downward" ? (
                      <ArrowDownRight className="h-5 w-5 text-rose-600" />
                    ) : (
                      <Minus className="h-5 w-5 text-slate-500" />
                    )}
                    <span>{forecastData.metrics.trend_direction}</span>
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
                  <div className="text-xs font-semibold text-slate-400 uppercase">
                    Expected Growth Rate
                  </div>
                  <div className="text-xl font-black text-brand-700 mt-1">
                    {forecastData.metrics.expected_growth_pct > 0 ? "+" : ""}
                    {forecastData.metrics.expected_growth_pct}%
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
                  <div className="text-xs font-semibold text-slate-400 uppercase">
                    Goodness-of-Fit (R²)
                  </div>
                  <div className="text-xl font-black text-slate-900 mt-1">
                    {forecastData.metrics.r_squared}
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
                  <div className="text-xs font-semibold text-slate-400 uppercase">
                    Projected Horizon Avg
                  </div>
                  <div className="text-xl font-black text-slate-900 mt-1">
                    {forecastData.metrics.projected_horizon_avg?.toLocaleString()}
                  </div>
                </div>
              </div>

              {/* Forecast Visual Chart with Confidence Interval Band */}
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
                <div className="border-b border-slate-100 pb-3 mb-4">
                  <h3 className="text-sm font-bold text-slate-800">
                    Predictive Trajectory with 95% Confidence Bounds
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Solid blue line represents historical actuals; dashed purple indicates projected trajectory; shaded area shows the 95% confidence interval band.
                  </p>
                </div>

                <div className="h-80 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart
                      data={forecastData.forecast_points}
                      margin={{ top: 10, right: 20, left: 10, bottom: 25 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                      <XAxis
                        dataKey="date"
                        tick={{ fill: "#64748b", fontSize: 11 }}
                        tickLine={false}
                      />
                      <YAxis
                        tick={{ fill: "#64748b", fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(v) => (typeof v === "number" ? v.toLocaleString() : v)}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#ffffff",
                          borderColor: "#e2e8f0",
                          borderRadius: "8px",
                          boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                          fontSize: "12px",
                        }}
                      />
                      <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />

                      {/* Confidence Band */}
                      <Area
                        type="monotone"
                        dataKey="upper_bound"
                        name="Upper 95% Bound"
                        stroke="none"
                        fill="#8b5cf6"
                        fillOpacity={0.15}
                      />
                      <Area
                        type="monotone"
                        dataKey="lower_bound"
                        name="Lower 95% Bound"
                        stroke="none"
                        fill="#ffffff"
                        fillOpacity={0.8}
                      />

                      {/* Historical Actuals */}
                      <Line
                        type="monotone"
                        dataKey="actual"
                        name="Historical Actual"
                        stroke="#3b82f6"
                        strokeWidth={2.5}
                        dot={{ r: 3, fill: "#3b82f6" }}
                        activeDot={{ r: 5 }}
                      />

                      {/* Predicted Future */}
                      <Line
                        type="monotone"
                        dataKey="predicted"
                        name="Forecast Projection"
                        stroke="#8b5cf6"
                        strokeWidth={2.5}
                        strokeDasharray="4 4"
                        dot={{ r: 3, fill: "#8b5cf6" }}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* AI Forecast Explainer & Business Intelligence Narrative */}
              {forecastData.ai_explanation && (
                <AIForecastExplainer
                  explanation={forecastData.ai_explanation}
                  onRefresh={runForecasting}
                  title={`AI Forecast Explainer: ${forecastTarget} Trajectory`}
                />
              )}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
