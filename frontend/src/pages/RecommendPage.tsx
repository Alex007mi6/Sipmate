import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api, getSessionId } from '../api/client'
import type { RecommendationItem, RecommendationResponse } from '../api/types'
import { BackChevron } from '../components/BackChevron'
import { useAuth } from '../context/AuthContext'
import {
  clearLadderStack,
  getRoundOriginId,
  getRoundPoints,
  hasLadderUndo,
  popLadderStep,
  pushLadderStep,
} from '../lib/ladderStack'

type AcceptResult = {
  ok: boolean
  points_awarded: number
  points_reversed?: number
  badges_awarded?: string[]
  badges_revoked?: string[]
  message?: string | null
  already_awarded?: boolean
}

type StepNotice = {
  pointsMessage: string
  fromName: string
  fromAbv: number
  toName: string
  toAbv: number
}

export function RecommendPage() {
  const { productId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuth()
  const [data, setData] = useState<RecommendationResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [undoBusy, setUndoBusy] = useState(false)
  const [canUndo, setCanUndo] = useState(() => hasLadderUndo())
  const [feedbackById, setFeedbackById] = useState<
    Record<number, { kind: 'ok' | 'error'; text: string }>
  >({})
  const [stepNotice, setStepNotice] = useState<StepNotice | null>(
    (location.state as StepNotice | null) ?? null,
  )
  const [undoNotice, setUndoNotice] = useState<string | null>(null)

  useEffect(() => {
    if (location.state) {
      setStepNotice(location.state as StepNotice)
      navigate(location.pathname, { replace: true, state: null })
    }
  }, [location.pathname, location.state, navigate])

  useEffect(() => {
    if (!productId) return
    setLoading(true)
    setError(null)
    setFeedbackById({})
    setCanUndo(hasLadderUndo())
    void api<RecommendationResponse>('/api/recommendations', {
      method: 'POST',
      body: JSON.stringify({
        product_id: Number(productId),
        top_k: 3,
        session_id: getSessionId(),
      }),
    })
      .then(setData)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [productId])

  function feedbackText(result: AcceptResult): string {
    if (!user) return 'Saved. Sign in for points.'
    if (result.already_awarded) return 'Already counted.'
    if (result.points_awarded > 0) {
      const badge =
        result.badges_awarded && result.badges_awarded.length
          ? ` · ${result.badges_awarded[0]}`
          : ''
      return `+${result.points_awarded} pts${badge}`
    }
    return result.message || 'Saved.'
  }

  async function accept(rec: RecommendationItem) {
    if (!data) return
    setBusyId(rec.product_id)
    setUndoNotice(null)
    setFeedbackById((prev) => {
      const next = { ...prev }
      delete next[rec.product_id]
      return next
    })
    try {
      const result = await api<AcceptResult>('/api/gamification/events', {
        method: 'POST',
        body: JSON.stringify({
          event_type: 'LIGHTER_CHOICE_ACCEPTED',
          selected_product_id: data.selected.id,
          recommended_product_id: rec.product_id,
          session_id: getSessionId(),
        }),
      })

      pushLadderStep({
        fromProductId: data.selected.id,
        toProductId: rec.product_id,
        pointsAwarded: result.points_awarded > 0 ? result.points_awarded : 0,
      })
      setCanUndo(true)

      navigate(`/recommend/${rec.product_id}`, {
        state: {
          pointsMessage: feedbackText(result),
          fromName: data.selected.name,
          fromAbv: data.selected.abv,
          toName: rec.name,
          toAbv: rec.abv,
        } satisfies StepNotice,
      })
    } catch (err) {
      setFeedbackById((prev) => ({
        ...prev,
        [rec.product_id]: {
          kind: 'error',
          text: err instanceof Error ? err.message : 'Failed',
        },
      }))
    } finally {
      setBusyId(null)
    }
  }

  async function undo() {
    const step = popLadderStep()
    if (!step) {
      setCanUndo(false)
      return
    }
    setUndoBusy(true)
    setStepNotice(null)
    try {
      const result = await api<AcceptResult>('/api/gamification/events', {
        method: 'POST',
        body: JSON.stringify({
          event_type: 'LIGHTER_CHOICE_UNDONE',
          selected_product_id: step.fromProductId,
          recommended_product_id: step.toProductId,
          session_id: getSessionId(),
        }),
      })
      const reversed = result.points_reversed ?? 0
      setUndoNotice(
        user && reversed > 0 ? `Undone · −${reversed} pts` : 'Undone',
      )
      setCanUndo(hasLadderUndo())
      navigate(`/recommend/${step.fromProductId}`)
    } catch (err) {
      pushLadderStep(step)
      setCanUndo(true)
      setUndoNotice(err instanceof Error ? err.message : 'Undo failed')
    } finally {
      setUndoBusy(false)
    }
  }

  function settle() {
    if (!data) return
    navigate(`/settled/${data.selected.id}`, {
      state: {
        originProductId: getRoundOriginId(data.selected.id),
        pointsEarned: getRoundPoints(),
      },
    })
  }

  if (loading) return <p className="muted">Loading…</p>
  if (error) return <div className="error" role="alert">{error}</div>
  if (!data) return null

  const selected = data.selected
  const noMoreSteps = data.recommendations.length === 0

  return (
    <section className="stack">
      <div className="page-head">
        <Link
          className="back-link"
          to="/drinks"
          aria-label="Back to drinks"
          onClick={() => clearLadderStack()}
        >
          <BackChevron />
        </Link>
        <h1 className="section-title">Lighter picks</h1>
        {canUndo ? (
          <button
            type="button"
            className="back-link undo-link"
            disabled={undoBusy}
            onClick={() => void undo()}
          >
            {undoBusy ? '…' : 'Undo'}
          </button>
        ) : null}
      </div>

      {stepNotice ? (
        <div className="success" role="status">
          ↓ {stepNotice.fromAbv.toFixed(1)}% → {stepNotice.toAbv.toFixed(1)}% ·{' '}
          {stepNotice.pointsMessage}
        </div>
      ) : null}

      {undoNotice ? (
        <div className="success" role="status">
          {undoNotice}
        </div>
      ) : null}

      <div className="drink-block now">
        <span className="chip">Now</span>
        <h2>{selected.name}</h2>
        <p className="meta">{selected.brand}</p>
        <div className="metric-row" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <div className="metric">
            <strong>{selected.abv.toFixed(1)}%</strong>
            <span>ABV</span>
          </div>
          <div className="metric">
            <strong>{selected.alcohol_grams?.toFixed(0) ?? '—'} g</strong>
            <span>Alcohol / glass</span>
          </div>
        </div>
        <button
          type="button"
          className={`btn btn-block ${canUndo ? 'btn-primary' : 'btn-secondary'}`}
          disabled={undoBusy || busyId !== null}
          onClick={settle}
        >
          {canUndo ? 'Stop here' : "I'll take this"}
        </button>
      </div>

      {noMoreSteps ? (
        <div className="panel stack">
          <p style={{ margin: 0, fontWeight: 700 }}>End of this ladder.</p>
          <div className="cta-row">
            <Link className="btn btn-primary" to={`/ladder/${selected.id}`}>
              Ladder
            </Link>
            <Link className="btn btn-secondary" to="/drinks" onClick={() => clearLadderStack()}>
              New drink
            </Link>
          </div>
        </div>
      ) : (
        <div className="stack">
          {data.recommendations.map((rec) => {
            const feedback = feedbackById[rec.product_id]
            const busy = busyId === rec.product_id
            return (
              <article key={rec.product_id} className="drink-block alt">
                <span className="chip">Next</span>
                <h2>{rec.name}</h2>
                <p className="meta">{rec.brand}</p>
                <div className="metric-row">
                  <div className="metric">
                    <strong>{rec.abv.toFixed(1)}%</strong>
                    <span>ABV</span>
                  </div>
                  <div className="metric">
                    <strong>{rec.taste_match_pct.toFixed(0)}%</strong>
                    <span>Match</span>
                  </div>
                  <div className="metric">
                    <strong>↓{rec.alcohol_ml_reduction_pct?.toFixed(0) ?? '—'}%</strong>
                    <span>Alcohol</span>
                  </div>
                </div>
                <div className="cta-row">
                  <button
                    type="button"
                    className="btn btn-accent"
                    disabled={busy || undoBusy}
                    onClick={() => void accept(rec)}
                  >
                    {busy ? '…' : 'Accept'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => navigate(`/ladder/${selected.id}`)}
                  >
                    Ladder
                  </button>
                </div>
                {feedback ? (
                  <div
                    className={feedback.kind === 'ok' ? 'success' : 'error'}
                    role="status"
                    style={{ marginTop: '0.65rem' }}
                  >
                    {feedback.text}
                  </div>
                ) : null}
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
