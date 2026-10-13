import React, { useEffect, useState } from "react";
import { useDataset } from "../context/DatasetContext";
import {
  getCpiOptions,
  getCpiForecast,
  loadCpiSample,
  extractErrorMessage,
} from "../api/client";
import type {
  CpiOptionsResponse,
  CpiForecastResponse,
  CpiPoint,
} from "../types/dataset";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import {
  LineChart as LineChartIcon,
  TrendingUp,
  Calendar,
  Layers,
  Sparkles,
  AlertTriangle,
  Info,
  ShieldAlert,
  ArrowUpRight,
  ArrowDownRight,
  FileSpreadsheet,
  RefreshCw,
  ShoppingBag,
  Sliders,
  CheckCircle2,
} from "lucide-react";

export default function CPIForecasting() {
  const { activeDataset, selectDataset } = useDataset();

  const [options, setOptions] = useState<CpiOptionsResponse | null>(null);
  const [isOptionsLoading, setIsOptionsLoading] = useState(false);
  const [optionsError, setOptionsError] = useState<string | null>(null);

  // Form Controls
  const [selectedMode, setSelectedMode] = useState<"auto" | "cpi" | "product_price" | "price_index">("auto");
  const [selectedPriceCol, setSelectedPriceCol] = useState<string>("");
  const [selectedDimension, setSelectedDimension] = useState<string>("");
  const [selectedValue, setSelectedValue] = useState<string>("All");
  const [horizonMonths, setHorizonMonths] = useState<number>(6);
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");

  // Forecast state
  const [forecast, setForecast] = useState<CpiForecastResponse | null>(null);
  const [isForecastLoading, setIsForecastLoading] = useState(false);
  const [forecastError, setForecastError] = useState<string | null>(null);
  const [isLoadingSample, setIsLoadingSample] = useState(false);

  // Fetch CPI capabilities when active dataset changes
  const fetchOptions = async (datasetId: number) => {
    setIsOptionsLoading(true);
    setOptionsError(null);
    setForecast(null);
    try {
      const res = await getCpiOptions(datasetId);
      setOptions(res);
      if (res.supported) {
        const dimCols = res.dimension_columns || [];
        const primaryDim = dimCols.length > 0 ? dimCols[0] : "";
        setSelectedDimension(primaryDim);
        setSelectedValue("All");
        setSelectedPriceCol(res.price_column || "");
        setSelectedMode(res.mode === "cpi" ? "cpi" : "auto");
        setStartDate(res.min_date || "");
        setEndDate(res.max_date || "");

        // Auto-run initial forecast
        triggerForecast(
          datasetId,
          res.mode === "cpi" ? "cpi" : "auto",
          primaryDim,
          "All",
          6,
          res.price_column,
          res.min_date,
          res.max_date
        );
      }
    } catch (e) {
      setOptionsError(extractErrorMessage(e));
    } finally {
      setIsOptionsLoading(false);
    }
  };

  const triggerForecast = async (
    datasetId: number,
    mode: "auto" | "cpi" | "product_price" | "price_index",
    dimCol: string,
    dimVal: string,
    horizon: number,
    priceCol?: string,
    start?: string,
    end?: string
  ) => {
    setIsForecastLoading(true);
    setForecastError(null);
    try {
      const res = await getCpiForecast(datasetId, {
        analysis_mode: mode,
        price_column: priceCol || undefined,
        dimension_column: dimCol || undefined,
        dimension_value: dimVal || "All",
        horizon_months: horizon,
        start_date: start || undefined,
        end_date: end || undefined,
      });
      setForecast(res);
    } catch (e) {
      // Do not display old results after a new request fails
      setForecast(null);
      setForecastError(extractErrorMessage(e));
    } finally {
      setIsForecastLoading(false);
    }
  };

  useEffect(() => {
    if (activeDataset?.id) {
      fetchOptions(activeDataset.id);
    }
  }, [activeDataset?.id]);

  const handleApplyForecast = () => {
    if (!activeDataset?.id) return;
    triggerForecast(
      activeDataset.id,
      selectedMode,
      selectedDimension,
      selectedValue,
      horizonMonths,
      selectedPriceCol,
      startDate,
      endDate
    );
  };

  const handleHorizonClick = (h: number) => {
    setHorizonMonths(h);
    if (activeDataset?.id) {
      triggerForecast(
        activeDataset.id,
        selectedMode,
        selectedDimension,
        selectedValue,
        h,
        selectedPriceCol,
        startDate,
        endDate
      );
    }
  };

  const handleModeChange = (mode: "auto" | "cpi" | "product_price" | "price_index") => {
    setSelectedMode(mode);
    if (activeDataset?.id) {
      triggerForecast(
        activeDataset.id,
        mode,
        selectedDimension,
        selectedValue,
        horizonMonths,
        selectedPriceCol,
        startDate,
        endDate
      );
    }
  };

  const handleLoadSampleCPI = async () => {
    setIsLoadingSample(true);
    setOptionsError(null);
    try {
      const newDs = await loadCpiSample();
      await selectDataset(newDs.id);
    } catch (e) {
      setOptionsError(extractErrorMessage(e));
    } finally {
      setIsLoadingSample(false);
    }
  };

  if (!activeDataset) {
    return (
      <div className="flex h-[60vh] flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-white p-12 text-center">
        <LineChartIcon className="h-12 w-12 text-brand-500 mb-3" />
        <h2 className="text-lg font-bold text-slate-800">No Active Dataset Selected</h2>
        <p className="text-xs text-slate-400 max-w-sm mt-1 mb-5">
          Please select or upload a dataset containing price or CPI time-series information to generate forecasts.
        </p>
        <button
          onClick={handleLoadSampleCPI}
          disabled={isLoadingSample}
          className="flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-brand-700 disabled:opacity-50 transition"
        >
          <FileSpreadsheet className="h-4 w-4" />
          <span>{isLoadingSample ? "Loading CPI Data..." : "Load Official Monthly CPI Dataset"}</span>
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <div className="border-b border-slate-200 pb-5 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Consumer Price Index & Price Forecasting System
            </h1>
            {options?.supported && forecast && (
              <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                forecast.mode === "cpi"
                  ? "bg-blue-100 text-blue-800"
                  : forecast.mode === "price_index"
                  ? "bg-indigo-100 text-indigo-800"
                  : "bg-emerald-100 text-emerald-800"
              }`}>
                {forecast.mode_label}
              </span>
            )}
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Empirically grounded time-series forecasting with Holt's exponential smoothing and 95% prediction intervals.
          </p>
        </div>

        <button
          onClick={handleLoadSampleCPI}
          disabled={isLoadingSample}
          className="inline-flex items-center gap-2 self-start md:self-auto rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 disabled:opacity-50 transition"
        >
          <FileSpreadsheet className="h-4 w-4 text-brand-600" />
          <span>{isLoadingSample ? "Loading CPI..." : "Load Official CPI Dataset"}</span>
        </button>
      </div>

      {/* Distinction Explainer Banner */}
      <div className="rounded-2xl border border-slate-200 bg-gradient-to-r from-slate-50 via-indigo-50/30 to-slate-50 p-4 shadow-2xs">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-800 mb-1">
          <Info className="h-4 w-4 text-brand-600" />
          <span>Analytical Modes & Methodology Distinction</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[11px] text-slate-600 mt-2">
          <div className="rounded-xl border border-slate-200/80 bg-white p-3 space-y-1">
            <span className="font-bold text-slate-900 flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-500 inline-block" />
              Product Price Forecast
            </span>
            <p className="text-slate-500 leading-relaxed">
              Forecasts nominal unit price trajectories (e.g. $USD) across items without index normalization.
            </p>
          </div>
          <div className="rounded-xl border border-slate-200/80 bg-white p-3 space-y-1">
            <span className="font-bold text-slate-900 flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-indigo-500 inline-block" />
              Price Index Estimate (Base = 100)
            </span>
            <p className="text-slate-500 leading-relaxed">
              Normalizes historical prices to baseline 100.0, enabling direct cross-product inflation comparison.
            </p>
          </div>
          <div className="rounded-xl border border-slate-200/80 bg-white p-3 space-y-1">
            <span className="font-bold text-slate-900 flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-blue-500 inline-block" />
              Consumer Price Index (CPI)
            </span>
            <p className="text-slate-500 leading-relaxed">
              Standardized macroeconomic benchmark measuring basket cost changes when authentic CPI is present.
            </p>
          </div>
        </div>
      </div>

      {/* Unsupported Dataset State */}
      {options && !options.supported && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/80 p-6 space-y-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-bold text-amber-900">
                Insufficient Time-Series Price Information
              </h3>
              <p className="text-xs text-amber-800 mt-1 leading-relaxed">
                {options.reason ||
                  "This dataset does not contain sufficient chronological price or index information for forecasting."}
              </p>
            </div>
          </div>
          <div className="pt-2">
            <button
              onClick={handleLoadSampleCPI}
              disabled={isLoadingSample}
              className="inline-flex items-center gap-2 rounded-xl bg-amber-700 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-amber-800 disabled:opacity-50 transition"
            >
              <FileSpreadsheet className="h-4 w-4" />
              <span>Load Official Monthly CPI Dataset (BLS 2021–2024)</span>
            </button>
          </div>
        </div>
      )}

      {/* Interactive Control Dashboard Bar */}
      {options?.supported && (
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-800 uppercase tracking-wider">
              <Sliders className="h-4 w-4 text-brand-600" />
              <span>Forecasting Parameters & Slicing</span>
            </div>
            {forecast && (
              <span className="text-[11px] text-slate-500 font-medium">
                Model: <code className="text-slate-800 font-semibold">{forecast.model_name}</code> • Fit RMSE: <code className="text-slate-800 font-semibold">{forecast.fit_rmse}</code>
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {/* Mode Selector */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-600">Analysis Mode</label>
              <select
                value={selectedMode}
                onChange={(e) => handleModeChange(e.target.value as any)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2 px-3 text-xs font-medium text-slate-800 focus:border-brand-500 focus:outline-hidden focus:ring-1 focus:ring-brand-500 cursor-pointer"
              >
                {options.mode === "cpi" && (
                  <option value="cpi">Consumer Price Index (CPI)</option>
                )}
                <option value="product_price">Product Price Forecast ($)</option>
                <option value="price_index">Price Index Estimate (Base = 100)</option>
              </select>
            </div>

            {/* Dimension Column Selector */}
            {options.dimension_columns && options.dimension_columns.length > 0 && (
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-600">Dimension</label>
                <select
                  value={selectedDimension}
                  onChange={(e) => {
                    setSelectedDimension(e.target.value);
                    setSelectedValue("All");
                  }}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2 px-3 text-xs font-medium text-slate-800 focus:border-brand-500 focus:outline-hidden focus:ring-1 focus:ring-brand-500 cursor-pointer"
                >
                  {options.dimension_columns.map((col) => (
                    <option key={col} value={col}>
                      {col}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Dimension Value Selector */}
            {selectedDimension && options.dimension_values?.[selectedDimension] && (
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-600">
                  Select {selectedDimension}
                </label>
                <select
                  value={selectedValue}
                  onChange={(e) => setSelectedValue(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2 px-3 text-xs font-medium text-slate-800 focus:border-brand-500 focus:outline-hidden focus:ring-1 focus:ring-brand-500 cursor-pointer"
                >
                  <option value="All">All {selectedDimension}s (Combined)</option>
                  {options.dimension_values[selectedDimension].map((val) => (
                    <option key={val} value={val}>
                      {val}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Forecast Horizon Selector (3m, 6m, 12m) */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-600">Forecast Horizon</label>
              <div className="grid grid-cols-3 gap-1 bg-slate-100 p-1 rounded-xl">
                {[3, 6, 12].map((h) => (
                  <button
                    key={h}
                    onClick={() => handleHorizonClick(h)}
                    className={`py-1.5 text-xs font-bold rounded-lg transition ${
                      horizonMonths === h
                        ? "bg-white text-brand-700 shadow-2xs"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    {h} Mos
                  </button>
                ))}
              </div>
            </div>

            {/* Apply Action Trigger */}
            <div className="flex items-end">
              <button
                onClick={handleApplyForecast}
                disabled={isForecastLoading}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-brand-600 py-2.5 px-4 text-xs font-bold text-white shadow-xs hover:bg-brand-700 disabled:opacity-50 transition cursor-pointer"
              >
                {isForecastLoading ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    <span>Forecasting...</span>
                  </>
                ) : (
                  <>
                    <TrendingUp className="h-4 w-4" />
                    <span>Apply Forecast</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {forecastError && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs font-medium text-rose-700 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{forecastError}</span>
        </div>
      )}

      {/* KPI Cards (4 Cards) */}
      {forecast && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Current Index / Price */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs space-y-2">
            <div className="flex items-center justify-between text-[11px] font-bold uppercase tracking-wider text-slate-400">
              <span>Current {forecast.mode === "cpi" ? "CPI" : "Price / Index"}</span>
              <Calendar className="h-4 w-4 text-slate-400" />
            </div>
            <div className="text-2xl font-extrabold text-slate-900">
              {forecast.current_index.toLocaleString()}
            </div>
            <div className="text-xs text-slate-500">
              Latest Actual Observation
            </div>
          </div>

          {/* Card 2: Forecasted Index at End of Horizon */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs space-y-2">
            <div className="flex items-center justify-between text-[11px] font-bold uppercase tracking-wider text-slate-400">
              <span>{forecast.horizon_months}-Mo Projected</span>
              <TrendingUp className="h-4 w-4 text-brand-600" />
            </div>
            <div className="text-2xl font-extrabold text-brand-600">
              {forecast.forecasted_index.toLocaleString()}
            </div>
            <div className="text-xs text-slate-500">
              Value at Month {forecast.horizon_months} ({forecast.forecast_end_date})
            </div>
          </div>

          {/* Card 3: Expected % Change */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs space-y-2">
            <div className="flex items-center justify-between text-[11px] font-bold uppercase tracking-wider text-slate-400">
              <span>Projected Change</span>
              {forecast.expected_change_pct >= 0 ? (
                <ArrowUpRight className="h-4 w-4 text-amber-500" />
              ) : (
                <ArrowDownRight className="h-4 w-4 text-emerald-500" />
              )}
            </div>
            <div className={`text-2xl font-extrabold flex items-center gap-1.5 ${
              forecast.expected_change_pct > 0 ? "text-amber-600" : "text-emerald-600"
            }`}>
              <span>{forecast.expected_change_pct > 0 ? `+${forecast.expected_change_pct}%` : `${forecast.expected_change_pct}%`}</span>
            </div>
            <div className="text-xs text-slate-500">
              Compounded Annual: {forecast.annualized_rate_pct}% / yr
            </div>
          </div>

          {/* Card 4: Historical Observations & Fit */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs space-y-2">
            <div className="flex items-center justify-between text-[11px] font-bold uppercase tracking-wider text-slate-400">
              <span>Dataset Depth</span>
              <Layers className="h-4 w-4 text-slate-400" />
            </div>
            <div className="text-2xl font-extrabold text-slate-900">
              {forecast.historical_observations} Periods
            </div>
            <div className="text-xs text-slate-500">
              Model MAPE: {forecast.fit_mape}%
            </div>
          </div>
        </div>
      )}

      {/* Main Forecast Chart */}
      {forecast && forecast.points && forecast.points.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
                <LineChartIcon className="h-5 w-5 text-brand-600" />
                {forecast.mode_label}: Historical vs. Projected Horizon ({forecast.horizon_months} Months)
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Forecast period: <strong>{forecast.forecast_start_date}</strong> to <strong>{forecast.forecast_end_date}</strong>. Solid indigo indicates historical values; dashed cyan shows model forecast trajectory with shaded 95% confidence intervals.
              </p>
            </div>
            <span className="text-xs font-semibold text-slate-500 bg-slate-100 px-2.5 py-1 rounded-lg">
              Scope: {forecast.selected_dimension_value}
            </span>
          </div>

          <div className="h-[360px] w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={forecast.points} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#64748B" }} tickLine={false} />
                <YAxis
                  tick={{ fontSize: 11, fill: "#64748B" }}
                  tickLine={false}
                  axisLine={false}
                  domain={["auto", "auto"]}
                />
                <Tooltip
                  formatter={(val: number, name: string) => {
                    const labelMap: Record<string, string> = {
                      actual: "Actual Historical",
                      predicted: "Model Forecast Trajectory",
                      upper_bound: "95% Upper CI",
                      lower_bound: "95% Lower CI",
                    };
                    const formatted = typeof val === "number" ? val.toFixed(2) : val;
                    return [formatted, labelMap[name] || name];
                  }}
                  contentStyle={{
                    backgroundColor: "#FFFFFF",
                    borderColor: "#E2E8F0",
                    borderRadius: "12px",
                    boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                    fontSize: "12px",
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 12, paddingTop: 10 }} />

                {/* Shaded 95% Confidence Interval Band */}
                <Area
                  type="monotone"
                  dataKey="upper_bound"
                  stroke="none"
                  fill="#E0F2FE"
                  fillOpacity={0.7}
                  name="95% Confidence Band"
                />
                <Area
                  type="monotone"
                  dataKey="lower_bound"
                  stroke="none"
                  fill="#FFFFFF"
                  fillOpacity={1}
                />

                {/* Historical Actual Line */}
                <Line
                  type="monotone"
                  dataKey="actual"
                  stroke="#4F46E5"
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: "#4F46E5" }}
                  name="Actual Historical"
                />

                {/* Model Forecast Line (Seamless bridge from last actual point) */}
                <Line
                  type="monotone"
                  dataKey="predicted"
                  stroke="#0284C7"
                  strokeWidth={2}
                  strokeDasharray="4 4"
                  dot={{ r: 3, fill: "#0284C7" }}
                  name="Forecast Trajectory"
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Consumer Purchasing Insights & Market Strategy */}
      {forecast && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <ShoppingBag className="h-5 w-5 text-brand-600" />
            <h2 className="text-base font-bold text-slate-800">
              Consumer Market & Purchasing Insights
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            {/* Purchasing Window Recommendation */}
            <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-4 space-y-2">
              <div className="font-bold text-slate-800 flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-amber-500" />
                <span>Purchasing Window Guidance</span>
              </div>
              <p className="text-slate-600 leading-relaxed font-medium">
                {forecast.purchasing_recommendation}
              </p>
            </div>

            {/* Historical Volatility & Inflation Risk */}
            <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-4 space-y-2">
              <div className="font-bold text-slate-800 flex items-center gap-2">
                <ActivityIcon className="h-4 w-4 text-indigo-600" />
                <span>Historical Volatility & Price Stability</span>
              </div>
              <p className="text-slate-600 leading-relaxed">
                Coefficient of Variation is <strong>{forecast.volatility_pct}%</strong> across the historical timeline,
                indicating {forecast.volatility_pct > 15 ? "elevated price fluctuation" : forecast.volatility_pct > 5 ? "moderate cyclical variance" : "stable and predictable price cadence"}.
              </p>
            </div>

            {/* Highest Growth Dimension */}
            <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-4 space-y-1.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Highest Historical Growth Dimension
              </span>
              <div className="font-bold text-slate-900 text-sm">
                {forecast.highest_growth_category}
              </div>
              <p className="text-slate-500">Fastest historical price escalation rate.</p>
            </div>

            {/* Lowest Growth Dimension */}
            <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-4 space-y-1.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Lowest Historical Growth Dimension
              </span>
              <div className="font-bold text-slate-900 text-sm">
                {forecast.lowest_growth_category}
              </div>
              <p className="text-slate-500">Most price-resilient / softening dimension.</p>
            </div>
          </div>

          {/* Compliance & Confidence Interval Disclaimers */}
          <div className="space-y-2">
            {forecast.confidence_interval_note && (
              <div className="flex items-start gap-2 rounded-xl bg-blue-50/60 p-3 text-[11px] text-blue-700 border border-blue-100">
                <Info className="h-4 w-4 text-blue-500 shrink-0 mt-0.5" />
                <span>{forecast.confidence_interval_note}</span>
              </div>
            )}
            <div className="flex items-start gap-2 rounded-xl bg-slate-50 p-3 text-[11px] text-slate-500 border border-slate-100">
              <ShieldAlert className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
              <span>{forecast.disclaimer}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ActivityIcon(props: { className?: string }) {
  return (
    <svg
      className={props.className}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
    </svg>
  );
}

