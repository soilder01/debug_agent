import type { ReactNode } from "react";

type SectionHeaderProps = {
  title: string;
  eyebrow?: string;
  description?: string;
};

export function SectionHeader({ title, eyebrow, description }: SectionHeaderProps) {
  return (
    <header className="section-header">
      {eyebrow ? <p className="section-header__eyebrow">{eyebrow}</p> : null}
      <h2>{title}</h2>
      {description ? <p className="section-header__description">{description}</p> : null}
    </header>
  );
}

type ProductSurfaceProps = SectionHeaderProps & {
  children: ReactNode;
  className?: string;
};

export function ProductSurface({ title, eyebrow, description, children, className = "" }: ProductSurfaceProps) {
  return (
    <section className={`product-surface ${className}`.trim()} aria-label={title}>
      <SectionHeader title={title} eyebrow={eyebrow} description={description} />
      <div className="product-surface__body">{children}</div>
    </section>
  );
}

type Metric = {
  label: string;
  value: ReactNode;
  helper?: string;
};

type MetricStripProps = {
  metrics: Metric[];
  label?: string;
};

export function MetricStrip({ metrics, label = "指标" }: MetricStripProps) {
  return (
    <dl className="metric-strip" aria-label={label}>
      {metrics.map((metric) => (
        <div className="metric-strip__item" key={metric.label}>
          <dt>{metric.label}</dt>
          <dd>{metric.value}</dd>
          {metric.helper ? <p>{metric.helper}</p> : null}
        </div>
      ))}
    </dl>
  );
}

type StatusBadgeProps = {
  tone: "critical" | "warning" | "success" | "neutral";
  children: ReactNode;
};

export function StatusBadge({ tone, children }: StatusBadgeProps) {
  return <span className={`status-badge status-badge--${tone}`}>{children}</span>;
}

type ActionRowProps = {
  children: ReactNode;
  label?: string;
};

export function ActionRow({ children, label = "操作" }: ActionRowProps) {
  return (
    <div className="action-row" aria-label={label}>
      {children}
    </div>
  );
}

type EmptyStateProps = {
  title: string;
  description?: string;
};

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <p className="empty-state__title">{title}</p>
      {description ? <p>{description}</p> : null}
    </div>
  );
}
