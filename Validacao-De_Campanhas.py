<?php
session_start();

const USER_FILE    = __DIR__ . '/users.json';
const HISTORY_FILE = __DIR__ . '/history.json';

require __DIR__ . '/vendor/autoload.php';

use PhpOffice\PhpSpreadsheet\IOFactory;
use PhpOffice\PhpSpreadsheet\Spreadsheet;
use PhpOffice\PhpSpreadsheet\Style\Fill;
use GuzzleHttp\Client;

define('MARGEM', 1.0);

function load_users(): array {
    return file_exists(USER_FILE)
        ? (json_decode(file_get_contents(USER_FILE), true) ?: [])
        : [];
}
function save_users(array $u): void {
    file_put_contents(USER_FILE, json_encode($u, JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE));
}
function load_history(): array {
    return file_exists(HISTORY_FILE)
        ? (json_decode(file_get_contents(HISTORY_FILE), true) ?: [])
        : [];
}
function save_history(array $h): void {
    file_put_contents(HISTORY_FILE, json_encode($h, JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE));
}
function add_history_record(int $sales, int $campaigns, float $total, string $user): void {
    $h = load_history();
    $h[] = [
        'timestamp'      => date('c'),
        'user'           => $user,
        'sales_count'    => $sales,
        'campaign_count' => $campaigns,
        'total_value'    => $total,
    ];
    save_history($h);
}

if (!file_exists(USER_FILE)) {
    save_users([
        'joaolucas'=>[
            'name'=>'joaolucas','email'=>'admin@local','phone'=>'',
            'password'=>password_hash('joao123', PASSWORD_DEFAULT),
            'age'=>'','company'=>'','sector'=>'','is_admin'=>true
        ]
    ]);
}

$users   = load_users();
$op      = $_GET['op'] ?? 'login';
$err     = '';
$msg     = '';
$userKey = $_SESSION['user'] ?? null;

// — Logout —
if (isset($_GET['logout'])) {
    session_destroy();
    header('Location:index.php');
    exit;
}

if ($op==='login') {
    if ($_SERVER['REQUEST_METHOD']==='POST') {
        $u = $_POST['user'] ?? '';
        $p = $_POST['pass'] ?? '';
        if (isset($users[$u]) && password_verify($p, $users[$u]['password'])) {
            $_SESSION['user'] = $u;
            header('Location:index.php?op=dashboard');
            exit;
        }
        $err = 'Usuário ou senha inválidos.';
    }
    echo <<<HTML
<!DOCTYPE html><html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Login</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body class="bg-light"><div class="container py-5"><div class="card mx-auto" style="max-width:360px"><div class="card-body">
<h4 class="text-center mb-4">Login</h4>
HTML;
    if ($err) echo "<div class='alert alert-danger'>".htmlspecialchars($err)."</div>";
    echo <<<HTML
<form method="post">
  <input name="user" class="form-control mb-2" placeholder="Usuário" required autofocus>
  <input name="pass" type="password" class="form-control mb-2" placeholder="Senha" required>
  <div class="d-flex justify-content-between mb-3">
    <a href="?op=forgot">Esqueci senha</a>
    <a href="?op=register">Cadastro</a>
  </div>
  <button class="btn btn-primary w-100">Entrar</button>
</form>
</div></div></div></body></html>
HTML;
    exit;
}

if ($op==='register') {
    if ($_SERVER['REQUEST_METHOD']==='POST') {
        $u=trim($_POST['user']??'');
        $e=trim($_POST['email']??'');
        $ph=trim($_POST['phone']??'');
        $pw=$_POST['pass']??''; $pw2=$_POST['pass2']??'';
        $age=trim($_POST['age']??''); $co=trim($_POST['company']??''); $se=trim($_POST['sector']??'');
        if (!$u||!$e||!$pw||!$pw2||$pw!==$pw2) {
            $err = 'Preencha corretamente.';
        } elseif (isset($users[$u])) {
            $err = 'Usuário já existe.';
        } else {
            $users[$u] = [
                'name'=>$u,'email'=>$e,'phone'=>$ph,
                'password'=>password_hash($pw,PASSWORD_DEFAULT),
                'age'=>$age,'company'=>$co,'sector'=>$se,'is_admin'=>false
            ];
            save_users($users);
            header('Location:index.php?op=login');
            exit;
        }
    }
    echo <<<HTML
<!DOCTYPE html><html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cadastro</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body class="bg-light"><div class="container py-5"><div class="card mx-auto" style="max-width:400px"><div class="card-body">
<h4 class="text-center mb-4">Cadastro</h4>
HTML;
    if ($err) echo "<div class='alert alert-danger'>".htmlspecialchars($err)."</div>";
    echo <<<HTML
<form method="post">
  <input name="user"     class="form-control mb-2" placeholder="Usuário" required>
  <input name="email"    type="email" class="form-control mb-2" placeholder="Email" required>
  <input name="phone"    class="form-control mb-2" placeholder="Telefone">
  <input name="pass"     type="password" class="form-control mb-2" placeholder="Senha" required>
  <input name="pass2"    type="password" class="form-control mb-2" placeholder="Repita Senha" required>
  <input name="age"      type="number" class="form-control mb-2" placeholder="Idade">
  <input name="company"  class="form-control mb-2" placeholder="Empresa">
  <input name="sector"   class="form-control mb-2" placeholder="Setor">
  <button class="btn btn-success w-100">Registrar</button>
</form>
</div></div></div></body></html>
HTML;
    exit;
}

if ($op==='forgot') {
    if ($_SERVER['REQUEST_METHOD']==='POST') {
        $msg = "Para redefinir sua senha, envie uma mensagem para o administrador: joaolucas";
    }
    echo <<<HTML
<!DOCTYPE html><html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Recuperar Senha</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body class="bg-light"><div class="container py-5"><div class="card mx-auto" style="max-width:360px"><div class="card-body">
<h4 class="text-center mb-4">Recuperar Senha</h4>
HTML;
    if($err) echo "<div class='alert alert-danger'>".htmlspecialchars($err)."</div>";
    if($msg) echo "<div class='alert alert-info'>".htmlspecialchars($msg)."</div>";
    echo <<<HTML
<form method="post">
  <div class="mb-3">
    <label class="form-label">Seu email cadastrado</label>
    <input name="email" type="email" class="form-control" required autofocus>
  </div>
  <button class="btn btn-primary w-100">Enviar Solicitação</button>
  <p class="mt-3 text-center"><a href="?op=login">Voltar ao login</a></p>
</form>
</div></div></div></body></html>
HTML;
    exit;
}

if(!$userKey){
    header('Location:index.php?op=login');
    exit;
}

if($op==='dashboard'){
    $history=load_history();
    echo <<<HTML
<!DOCTYPE html><html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body class="bg-light"><div class="container py-5">
<nav class="mb-4"><a href="?op=dashboard">Dashboard</a> | <a href="?op=profiles">Gerenciar Usuários</a> | <a href="?op=validate">Validação</a> | <a href="?logout">Sair</a></nav>
<h3>Histórico Geral</h3>
<table class="table table-striped"><thead><tr><th>Data</th><th>Usuário</th><th>#Vendas</th><th>#Campanhas</th><th>Valor Total</th></tr></thead><tbody>
HTML;
    foreach($history as $rec){
        echo "<tr><td>".htmlspecialchars($rec['timestamp'])."</td><td>".htmlspecialchars($rec['user'])."</td><td>".intval($rec['sales_count'])."</td><td>".intval($rec['campaign_count'])."</td><td>R$ ".number_format($rec['total_value'],2,',','.')."</td></tr>";
    }
    echo "</tbody></table></div></body></html>";
    exit;
}

if($op==='profiles'){
    if(!$users[$userKey]['is_admin']){ header('Location:index.php?op=dashboard'); exit; }
    echo <<<HTML
<!DOCTYPE html><html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gerenciar Usuários</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body class="bg-light"><div class="container py-5">
<nav class="mb-4"><a href="?op=dashboard">Dashboard</a> | <a href="?op=profiles">Gerenciar Usuários</a> | <a href="?op=validate">Validação</a> | <a href="?logout">Sair</a></nav>
<div class="mb-3">
  <a href="?op=create" class="btn btn-sm btn-primary">Novo Usuário/Admin</a>
</div>
<h3>Usuários</h3>
<table class="table table-bordered"><thead><tr><th>Usuário</th><th>Email</th><th>Admin</th><th>Ações</th></tr></thead><tbody>
HTML;
    foreach($users as $uname=>$ud){
        $btnGrant = $ud['is_admin']
            ? "<a href='?op=grant&user=$uname' class='btn btn-sm btn-warning'>Rebaixar</a>"
            : "<a href='?op=grant&user=$uname' class='btn btn-sm btn-success'>Promover</a>";
        $btnEdit = "<a href='?op=edit&user=$uname' class='btn btn-sm btn-secondary mx-1'>Editar</a>";
        $btnDel  = ($uname!==$userKey)
            ? "<a href='?op=delete&user=$uname' class='btn btn-sm btn-danger' onclick=\"return confirm('Excluir?')\">Excluir</a>"
            : "";
        echo "<tr><td>".htmlspecialchars($uname)."</td><td>".htmlspecialchars($ud['email'])."</td><td>".($ud['is_admin']?'Sim':'Não')."</td><td>$btnGrant $btnEdit $btnDel</td></tr>";
    }
    echo "</tbody></table></div></body></html>";
    exit;
}

if ($op === 'create') {
    if (!$users[$userKey]['is_admin']) {
        header('Location:index.php?op=dashboard');
        exit;
    }
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $u      = trim($_POST['user'] ?? '');
        $email  = trim($_POST['email'] ?? '');
        $phone  = trim($_POST['phone'] ?? '');
        $pass   = $_POST['pass'] ?? '';
        $pass2  = $_POST['pass2'] ?? '';
        $age    = trim($_POST['age'] ?? '');
        $co     = trim($_POST['company'] ?? '');
        $se     = trim($_POST['sector'] ?? '');
        $isAdm  = isset($_POST['is_admin']) ? true : false;
        if (!$u || !$email || !$pass || $pass !== $pass2) {
            $err = 'Preencha usuário, email e senha corretamente.';
        } elseif (isset($users[$u])) {
            $err = 'Usuário já existe.';
        } else {
            $users[$u] = [
                'name'     => $u,
                'email'    => $email,
                'phone'    => $phone,
                'password' => password_hash($pass, PASSWORD_DEFAULT),
                'age'      => $age,
                'company'  => $co,
                'sector'   => $se,
                'is_admin' => $isAdm
            ];
            save_users($users);
            header('Location:index.php?op=profiles');
            exit;
        }
    }
    echo <<<HTML
<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Novo Usuário/Admin</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-light"><div class="container py-5"><div class="card mx-auto" style="max-width:400px"><div class="card-body">
<h4 class="text-center mb-4">Criar Usuário/Admin</h4>
HTML;
    if (!empty($err)) echo "<div class='alert alert-danger'>".htmlspecialchars($err)."</div>";
    echo <<<HTML
<form method="post">
  <input name="user"     class="form-control mb-2" placeholder="Usuário (login)" required autofocus>
  <input name="email"    type="email" class="form-control mb-2" placeholder="Email" required>
  <input name="phone"    class="form-control mb-2" placeholder="Telefone">
  <input name="pass"     type="password" class="form-control mb-2" placeholder="Senha" required>
  <input name="pass2"    type="password" class="form-control mb-2" placeholder="Repita Senha" required>
  <div class="form-check mb-3">
    <input class="form-check-input" type="checkbox" name="is_admin" id="is_admin">
    <label class="form-check-label" for="is_admin">Administrador?</label>
  </div>
  <input name="age"      type="number" class="form-control mb-2" placeholder="Idade">
  <input name="company"  class="form-control mb-2" placeholder="Empresa">
  <input name="sector"   class="form-control mb-2" placeholder="Setor">
  <button class="btn btn-primary w-100">Criar</button>
  <p class="mt-3 text-center"><a href="?op=profiles">Cancelar</a></p>
</form>
</div></div></div></body></html>
HTML;
    exit;
}

if($op==='delete'){
    $d=$_GET['user']??'';
    if($users[$userKey]['is_admin']&&$d&&$d!==$userKey&&isset($users[$d])){
        unset($users[$d]); save_users($users);
    }
    header('Location:index.php?op=profiles');exit;
}

if($op==='grant'){
    $t=$_GET['user']??'';
    if($users[$userKey]['is_admin']&&$t!==$userKey&&isset($users[$t])){
        $users[$t]['is_admin']=!$users[$t]['is_admin']; save_users($users);
    }
    header('Location:index.php?op=profiles');exit;
}

if($op==='edit'){
    $t=$_GET['user']??'';
    if(!$users[$userKey]['is_admin']||!isset($users[$t])){
        header('Location:index.php?op=profiles');exit;
    }
    if($_SERVER['REQUEST_METHOD']==='POST'){
        $ud=&$users[$t];
        $ud['email']   = $_POST['email'];
        $ud['phone']   = $_POST['phone'];
        $ud['age']     = $_POST['age'];
        $ud['company'] = $_POST['company'];
        $ud['sector']  = $_POST['sector'];
        if(!empty($_POST['pass'])&&$_POST['pass']===$_POST['pass2']){
            $ud['password']=password_hash($_POST['pass'],PASSWORD_DEFAULT);
        }
        save_users($users);
        header('Location:index.php?op=profiles');exit;
    }
    $ud=$users[$t];
    echo <<<HTML
<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Editar $t</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head><body class="bg-light"><div class="container py-5"><div class="card mx-auto" style="max-width:400px"><div class="card-body"><h4 class="text-center mb-4">Editar $t</h4><form method="post">
  <input class="form-control mb-2" name="email"    type="email" value="{$ud['email']}" required>
  <input class="form-control mb-2" name="phone"    value="{$ud['phone']}">
  <input class="form-control mb-2" name="age"      type="number" value="{$ud['age']}">
  <input class="form-control mb-2" name="company"  value="{$ud['company']}">
  <input class="form-control mb-2" name="sector"   value="{$ud['sector']}">
  <hr>
  <input class="form-control mb-2" name="pass"     type="password" placeholder="Nova Senha (opcional)">
  <input class="form-control mb-3" name="pass2"    type="password" placeholder="Repita Senha">
  <button class="btn btn-primary w-100">Salvar</button>
</form><p class="mt-3 text-center"><a href="?op=profiles">Voltar</a></p></div></div></div></body></html>
HTML;
    exit;
}

if($op==='validate'){
    if($_SERVER['REQUEST_METHOD']==='POST'){
        $camp=IOFactory::load($_FILES['campanha']['tmp_name'])->getActiveSheet()->toArray(null,true,true,true);
        $vend=IOFactory::load($_FILES['vendas']['tmp_name'])->getActiveSheet()->toArray(null,true,true,true);
        array_shift($camp); array_shift($vend);
        $sales=count($vend);
        $campaigns=count($camp);
        $total=0; foreach($vend as $r){ $v=floatval(str_replace(',','.',preg_replace('/[^0-9,.\-]/','',$r['W']))); $total+=$v; }
        add_history_record($sales,$campaigns,$total,$userKey);

        $xlsx=processa($_FILES['campanha']['tmp_name'],$_FILES['vendas']['tmp_name']);
        header('Content-Type:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
        header('Content-Disposition:attachment;filename="resultado.xlsx"');
        IOFactory::createWriter($xlsx,'Xlsx')->save('php://output');
        exit;
    }
    echo <<<HTML
<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Validação de Vendas</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head><body class="bg-light"><div class="container py-5"><div class="card mx-auto" style="max-width:600px"><div class="card-body">
<h4 class="text-center mb-4">Validação de Vendas</h4><form method="post" enctype="multipart/form-data">
  <input type="file" name="campanha" class="form-control mb-3" required>
  <input type="file" name="vendas"    class="form-control mb-3" required>
  <button class="btn btn-primary w-100">Processar & Baixar</button>
</form></div></div></div></body></html>
HTML;
    exit;
}

// Default
header('Location:index.php?op=dashboard');
exit;

function processa(string $campFile,string $vendFile):Spreadsheet {
    $sheetCamp=IOFactory::load($campFile)->getActiveSheet()->toArray(null,true,true,true);
    $sheetVend=IOFactory::load($vendFile)->getActiveSheet()->toArray(null,true,true,true);
    array_shift($sheetCamp); array_shift($sheetVend);
    $campMap=[];
    foreach($sheetCamp as $r){
        $mp=trim($r['A']); $sku=trim($r['B']);
        $val=preg_replace('/[^0-9,.\-]/','',$r['D']);
        $p=floatval(str_replace(',','.',$val));
        if($mp&&$sku&&$p>0) $campMap[$mp][$sku][]=$p;
    }
    $out=new Spreadsheet(); $sh=$out->getActiveSheet();
    $sh->fromArray(['Marketplace','SKU','Valor Venda','Status','% Erro','Justificativa'],null,'A1');
    $rn=2;
    foreach($sheetVend as $r){
        $mpv=trim($r['I']); $skv=trim($r['AC']);
        $val=floatval(str_replace(',','.',preg_replace('/[^0-9,.\-]/','',$r['W'])));
        $pcs=$campMap[$mpv][$skv]??[];
        $st=empty($pcs)?'Sem SKU':'Erro'; $pe=''; $just='';
        if($pcs){
            foreach($pcs as $pc){
                if(abs($val-$pc)<1e-5){ $st='Correto'; break; }
                $p=($val-$pc)/$pc*100;
                if(abs($p)<=MARGEM){ $st='Correto'; $pe=round($p,2); break; }
            }
            if($st==='Erro'){
                $cl=null;
                foreach($pcs as $pc){
                    if($cl===null||abs($pc-$val)<abs($cl-$val)) $cl=$pc;
                }
                if($cl!==null) $pe=round((($val-$cl)/$cl)*100,2);
            }
        }
        $cols=['Correto'=>'FFCCFFCC','Sem SKU'=>'FFCCCCFF','Erro'=>'FFFF6666'];
        $sh->setCellValue("A$rn",$mpv)
           ->setCellValue("B$rn",$skv)
           ->setCellValue("C$rn",$val)
           ->setCellValue("D$rn",$st)
           ->setCellValue("E$rn",$pe)
           ->setCellValue("F$rn",$just);
        $fill=$sh->getStyle("D$rn")->getFill()->setFillType(Fill::FILL_SOLID);
        $fill->getStartColor()->setARGB($cols[$st]??'FFFF6666');
        $rn++;
    }
    return $out;
}
