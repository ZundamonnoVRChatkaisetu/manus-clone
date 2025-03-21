import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * cn関数 - Tailwindのクラスをマージするためのユーティリティ関数
 * クラス名の競合を解決し、最適化されたクラスリストを生成します
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * formatDate関数 - 日付を指定された形式にフォーマットする関数
 */
export function formatDate(date: Date | string): string {
  if (!date) {
    return '日時不明';
  }
  
  let dateObj: Date;
  
  try {
    // 文字列の場合は Date オブジェクトに変換
    dateObj = typeof date === 'string' ? new Date(date) : date;
    
    // 有効な日付かチェック
    if (isNaN(dateObj.getTime())) {
      console.error('Invalid date:', date);
      return '日時不明';
    }
    
    return new Intl.DateTimeFormat("ja-JP", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(dateObj);
  } catch (error) {
    console.error('Error formatting date:', error, date);
    return '日時不明';
  }
}

/**
 * 指定されたミリ秒だけ処理を遅延させる関数
 */
export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
