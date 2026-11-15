export default function OfflineBanner({ offline, savedAt }) {
  if (!offline) return null;
  const when = savedAt ? new Date(savedAt).toLocaleString() : 'earlier';
  return (
    <div className="alert alert-warn">
      📴 You are offline. Showing information saved on this phone ({when}).
    </div>
  );
}
