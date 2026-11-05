import { useEffect, useRef } from 'react'
import type { Meta } from '../api/client'

interface Props {
  meta: Meta | null
  threshold: number
  onClose: () => void
}

export default function AboutPanel({ meta, threshold, onClose }: Props) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    ref.current?.showModal()
  }, [])

  return (
    <dialog ref={ref} className="about" onClose={onClose} aria-labelledby="about-title">
      <h2 id="about-title">À propos des données</h2>
      <p>
        <strong>La perte de couvert arboré n’est pas de la déforestation.</strong> En France, la
        surface forestière augmente. Les pertes détectées par satellite correspondent surtout à des{' '}
        <strong>coupes rases</strong> (exploitation forestière), des <strong>incendies</strong>, des{' '}
        <strong>tempêtes</strong> et des <strong>dépérissements</strong> (scolytes, sécheresse). Une
        perte est souvent suivie d’une repousse.
      </p>
      <h3>Méthode</h3>
      <ul>
        <li>
          Forêt : pixels de 30 m dont le couvert arboré en 2000 est ≥ {threshold} % (Hansen/UMD).
        </li>
        <li>
          Perte annuelle : pixels Hansen marqués « perdus » chaque année, dans la forêt ainsi
          définie. Les totaux régionaux et nationaux sont la somme des départements.
        </li>
        <li>
          Alertes : DIST-ALERT (Landsat + Sentinel-2 harmonisés), perturbations de la végétation
          restreintes aux pixels forestiers, agrégées par semaine ISO. Niveaux de confiance fournis
          par GFW : nominale et élevée. L’historique interrogeable commence le 24 septembre 2025.
        </li>
        <li>
          Anomalie : semaine dont la surface d’alertes dépasse de 2 écarts-types la référence. La
          référence est la moyenne des 12 semaines précédentes, puis, dès 2 années d’historique, la
          même semaine des années précédentes.
        </li>
        <li>
          Sur la carte, le filtre de couvert des tuiles d’alertes GFW utilise le couvert arboré de
          2010, alors que les statistiques utilisent celui de 2000 : de légers écarts sont
          possibles.
        </li>
      </ul>
      <h3>Sources et licences</h3>
      <ul>
        {(meta?.sources ?? []).map((s) => (
          <li key={s.id}>
            <a href={s.url} target="_blank" rel="noreferrer">
              {s.name}
            </a>{' '}
            — {s.provider} — {s.licence}
          </li>
        ))}
      </ul>
      {meta && (
        <>
          <h3>Versions et mises à jour</h3>
          <ul>
            <li>Hansen : {meta.versions.hansen?.join(', ') || '—'}</li>
            <li>DIST-ALERT : {meta.versions.alerts?.join(', ') || '—'}</li>
            <li>Limites administratives : {meta.versions.boundaries?.join(', ') || '—'}</li>
            <li>Dernière alerte : {meta.latest_alert_date ?? '—'}</li>
          </ul>
          <p>
            <a href={meta.dbt_docs_url} target="_blank" rel="noreferrer">
              Documentation des modèles de données (dbt docs)
            </a>
          </p>
        </>
      )}
      <form method="dialog">
        <button type="submit">Fermer</button>
      </form>
    </dialog>
  )
}
