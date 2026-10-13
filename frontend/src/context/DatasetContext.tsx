import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import {
  extractErrorMessage,
  getDataset,
  listDatasets,
  loadSampleDataset,
  deleteDataset as apiDeleteDataset,
} from "../api/client";
import type { DatasetDetail, DatasetSummary } from "../types/dataset";

interface DatasetContextType {
  datasets: DatasetSummary[];
  activeDataset: DatasetDetail | null;
  activeDatasetId: number | null;
  isLoading: boolean;
  error: string | null;
  refreshDatasets: () => Promise<DatasetSummary[]>;
  selectDataset: (id: number) => Promise<void>;
  loadSample: () => Promise<void>;
  deleteDatasetById: (id: number) => Promise<void>;
  setActiveDatasetDetail: (detail: DatasetDetail) => void;
  clearError: () => void;
}

const DatasetContext = createContext<DatasetContextType | undefined>(undefined);

export const DatasetProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [activeDataset, setActiveDataset] = useState<DatasetDetail | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const refreshDatasets = useCallback(async () => {
    try {
      const list = await listDatasets();
      setDatasets(list);
      return list;
    } catch (err) {
      setError(extractErrorMessage(err));
      return [];
    }
  }, []);

  const selectDataset = useCallback(async (id: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const detail = await getDataset(id);
      setActiveDataset(detail);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadSample = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const detail = await loadSampleDataset();
      await refreshDatasets();
      setActiveDataset(detail);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [refreshDatasets]);

  const deleteDatasetById = useCallback(
    async (id: number) => {
      setError(null);
      try {
        await apiDeleteDataset(id);
        if (activeDataset?.id === id) {
          setActiveDataset(null);
        }
        await refreshDatasets();
      } catch (err) {
        setError(extractErrorMessage(err));
      }
    },
    [activeDataset, refreshDatasets]
  );

  const setActiveDatasetDetail = useCallback((detail: DatasetDetail) => {
    setActiveDataset(detail);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  useEffect(() => {
    refreshDatasets().then((list) => {
      // Auto-select first dataset if available and none selected
      if (list && list.length > 0 && !activeDataset) {
        selectDataset(list[0].id);
      }
    });
  }, [refreshDatasets]);

  return (
    <DatasetContext.Provider
      value={{
        datasets,
        activeDataset,
        activeDatasetId: activeDataset?.id ?? null,
        isLoading,
        error,
        refreshDatasets,
        selectDataset,
        loadSample,
        deleteDatasetById,
        setActiveDatasetDetail,
        clearError,
      }}
    >
      {children}
    </DatasetContext.Provider>
  );
};

export function useDataset(): DatasetContextType {
  const context = useContext(DatasetContext);
  if (!context) {
    throw new Error("useDataset must be used within a DatasetProvider");
  }
  return context;
}
