import pytest

from tools import ais_scenario_player as cli


@pytest.mark.parametrize("loop", [False, True])
def test_replay_loop_and_interrupt_close_ports(monkeypatch, capsys, loop):
    opened = []
    calls = []
    delays = []
    records = [object()]

    class Port:
        def __init__(self, port, baud):
            self.closed = False
            opened.append(self)
        def close(self):
            self.closed = True

    def play(items, **kwargs):
        assert items is records
        assert not any(port.closed for port in opened)
        assert kwargs['own_nmea_exporters'] == opened[:1]
        assert kwargs['aivdm_exporters'] == opened[1:]
        calls.append(kwargs)
        if len(calls) == 2:
            raise KeyboardInterrupt

    args = ['player', '--timeline', 'test.jsonl', '--own-nmea-serial', 'COM11',
            '--target-aivdm-serial', 'COM12', '--replay-speed', '2']
    if loop:
        args.append('--loop')
    monkeypatch.setattr(cli.sys, 'argv', args)
    monkeypatch.setattr(cli, 'read_timeline_jsonl', lambda _: records)
    monkeypatch.setattr(cli, 'SerialExporter', Port)
    monkeypatch.setattr(cli, 'play_timeline', play)
    monkeypatch.setattr(cli.time, 'sleep', delays.append)
    assert cli.main() == 0
    assert len(opened) == 2 and all(port.closed for port in opened)
    assert len(calls) == (2 if loop else 1)
    assert delays == ([0.5] if loop else [])
    if loop:
        assert 'Playback stopped.' in capsys.readouterr().out


def test_loop_rejects_empty_timeline(monkeypatch):
    monkeypatch.setattr(cli.sys, 'argv', ['player', '--timeline', 'empty.jsonl', '--loop'])
    monkeypatch.setattr(cli, 'read_timeline_jsonl', lambda _: [])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
